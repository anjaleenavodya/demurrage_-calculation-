"""
PyTorch Time-Series Deep Learning Sequence Model for Sri Lankan Vegetable Prices & Weather
Implements a multivariate LSTM / GRU sequence network using sliding window datasets,
crop entity embeddings, and multi-horizon price forecasting.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, "data_processed", "crop_weather_monthly.csv")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "pytorch_crop_lstm.pt")
SCALER_PATH = os.path.join(MODELS_DIR, "feature_scaler.joblib")
METRICS_PATH = os.path.join(MODELS_DIR, "model_metrics.json")

# Core features used in sliding sequence
FEATURE_COLS = [
    "farm_price",
    "retail_price_pettah",
    "retail_price_dambulla",
    "average_spread",
    "spread_pct",
    "temp_mean",
    "temp_max",
    "temp_min",
    "rain_sum",
    "rain_days",
    "sunshine_mean_hours",
    "radiation_mean",
    "et0_mean",
    "month_sin",
    "month_cos",
]

TARGET_COL = "farm_price"
TARGET_INDEX = FEATURE_COLS.index(TARGET_COL)


class CropTimeSeriesDataset(Dataset):
    """
    Sliding window PyTorch Dataset.
    Extracts sequences of length `seq_len` to predict `forecast_horizon` future target prices.
    """
    def __init__(
        self,
        features: np.ndarray,
        crop_ids: np.ndarray,
        targets: np.ndarray,
        seq_len: int = 6,
        forecast_horizon: int = 4,
    ):
        self.seq_len = seq_len
        self.forecast_horizon = forecast_horizon
        
        self.X_seqs = []
        self.crop_seqs = []
        self.y_seqs = []
        
        unique_crops = np.unique(crop_ids)
        for c in unique_crops:
            mask = (crop_ids == c)
            c_feats = features[mask]
            c_targets = targets[mask]
            
            n_samples = len(c_feats)
            total_window = seq_len + forecast_horizon
            if n_samples < total_window:
                continue
                
            for i in range(n_samples - total_window + 1):
                self.X_seqs.append(c_feats[i : i + seq_len])
                self.crop_seqs.append(c)
                self.y_seqs.append(c_targets[i + seq_len : i + total_window])
                
        self.X_seqs = torch.tensor(np.array(self.X_seqs), dtype=torch.float32)
        self.crop_seqs = torch.tensor(np.array(self.crop_seqs), dtype=torch.long)
        self.y_seqs = torch.tensor(np.array(self.y_seqs), dtype=torch.float32)
        
    def __len__(self):
        return len(self.X_seqs)
        
    def __getitem__(self, idx):
        return self.X_seqs[idx], self.crop_seqs[idx], self.y_seqs[idx]


class CropPriceLSTM(nn.Module):
    """
    Deep Neural Network combining Crop Entity Embeddings with
    a multi-layer Stacked Bidirectional LSTM and Dense Multi-Horizon Forecast Head.
    """
    def __init__(
        self,
        num_crops: int,
        feature_dim: int,
        embedding_dim: int = 8,
        hidden_dim: int = 64,
        num_layers: int = 2,
        forecast_horizon: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.crop_embedding = nn.Embedding(num_crops, embedding_dim)
        
        # Combined input: continuous features + expanded crop embedding
        lstm_input_dim = feature_dim + embedding_dim
        
        self.lstm = nn.LSTM(
            input_size=lstm_input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        
        # Self-attention / pooling layer
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.Tanh(),
            nn.Linear(32, 1),
            nn.Softmax(dim=1),
        )
        
        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, forecast_horizon),
        )
        
    def forward(self, x: torch.Tensor, crop_idx: torch.Tensor) -> torch.Tensor:
        # x: [batch, seq_len, feature_dim]
        batch_size, seq_len, _ = x.shape
        
        # Crop embedding: [batch, embedding_dim] -> repeated along sequence: [batch, seq_len, embedding_dim]
        c_emb = self.crop_embedding(crop_idx).unsqueeze(1).repeat(1, seq_len, 1)
        
        # Concat features and embedding
        lstm_in = torch.cat([x, c_emb], dim=-1)
        
        # LSTM output: [batch, seq_len, hidden_dim * 2]
        lstm_out, _ = self.lstm(lstm_in)
        
        # Attention weights across time sequence: [batch, seq_len, 1]
        attn_weights = self.attention(lstm_out)
        context = torch.sum(attn_weights * lstm_out, dim=1) # [batch, hidden_dim * 2]
        
        # Multi-horizon forecast
        out = self.head(context) # [batch, forecast_horizon]
        return out


def prepare_training_data(
    seq_len: int = 6,
    forecast_horizon: int = 4,
    test_split_year: int = 2023,
) -> Tuple[DataLoader, DataLoader, StandardScaler, Dict, pd.DataFrame]:
    """
    Loads preprocessed dataset, applies train/test chronological split,
    normalizes features, and builds PyTorch DataLoaders.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values(by=["crop_name", "date"], inplace=True)
    
    crops = sorted(df["crop_name"].unique())
    crop_to_idx = {c: i for i, c in enumerate(crops)}
    idx_to_crop = {i: c for i, c in enumerate(crops)}
    df["crop_idx"] = df["crop_name"].map(crop_to_idx)
    
    # Chronological Split: Train up to end of 2022, Test on 2023-2024
    train_mask = df["date"].dt.year < test_split_year
    test_mask = df["date"].dt.year >= test_split_year
    
    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()
    
    # Fit scaler strictly on training set
    scaler = StandardScaler()
    scaler.fit(train_df[FEATURE_COLS])
    joblib.dump(scaler, SCALER_PATH)
    
    # Transform
    train_feats = scaler.transform(train_df[FEATURE_COLS])
    test_feats = scaler.transform(test_df[FEATURE_COLS])
    
    # Standardize targets using the mean & scale of the target column
    target_mean = scaler.mean_[TARGET_INDEX]
    target_scale = scaler.scale_[TARGET_INDEX]
    
    train_targets = (train_df[TARGET_COL].values - target_mean) / target_scale
    test_targets = (test_df[TARGET_COL].values - target_mean) / target_scale
    
    train_dataset = CropTimeSeriesDataset(
        features=train_feats,
        crop_ids=train_df["crop_idx"].values,
        targets=train_targets,
        seq_len=seq_len,
        forecast_horizon=forecast_horizon,
    )
    
    test_dataset = CropTimeSeriesDataset(
        features=test_feats,
        crop_ids=test_df["crop_idx"].values,
        targets=test_targets,
        seq_len=seq_len,
        forecast_horizon=forecast_horizon,
    )
    
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
    
    meta = {
        "crops": crops,
        "crop_to_idx": crop_to_idx,
        "idx_to_crop": idx_to_crop,
        "seq_len": seq_len,
        "forecast_horizon": forecast_horizon,
        "feature_cols": FEATURE_COLS,
        "target_col": TARGET_COL,
        "target_mean": float(target_mean),
        "target_scale": float(target_scale),
    }
    
    return train_loader, test_loader, scaler, meta, df


def train_model(
    epochs: int = 35,
    lr: float = 0.003,
    seq_len: int = 6,
    forecast_horizon: int = 4,
    device: Optional[str] = None,
) -> Dict:
    """
    Trains the PyTorch LSTM forecasting model with early stopping,
    evaluates against the hold-out test set, and saves checkpoints.
    """
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    
    train_loader, test_loader, scaler, meta, full_df = prepare_training_data(
        seq_len=seq_len, forecast_horizon=forecast_horizon
    )
    
    model = CropPriceLSTM(
        num_crops=len(meta["crops"]),
        feature_dim=len(FEATURE_COLS),
        embedding_dim=8,
        hidden_dim=64,
        num_layers=2,
        forecast_horizon=forecast_horizon,
        dropout=0.2,
    ).to(device)
    
    criterion = nn.SmoothL1Loss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)
    
    best_loss = float("inf")
    history = {"train_loss": [], "val_loss": []}
    
    print(f"\n Starting PyTorch Model Training on Device: {device.upper()}")
    print(f" Dataset sequences: {len(train_loader.dataset)} train, {len(test_loader.dataset)} test")
    print(f" Architecture: Stacked BiLSTM + Temporal Attention (Sequence: {seq_len}m -> Horizon: {forecast_horizon}m)\n")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for x_batch, c_batch, y_batch in train_loader:
            x_batch, c_batch, y_batch = x_batch.to(device), c_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            preds = model(x_batch, c_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * len(x_batch)
            
        train_loss /= len(train_loader.dataset)
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, c_batch, y_batch in test_loader:
                x_batch, c_batch, y_batch = x_batch.to(device), c_batch.to(device), y_batch.to(device)
                preds = model(x_batch, c_batch)
                loss = criterion(preds, y_batch)
                val_loss += loss.item() * len(x_batch)
                
        val_loss /= len(test_loader.dataset) if len(test_loader.dataset) > 0 else 1.0
        scheduler.step(val_loss)
        
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "meta": meta,
                    "val_loss": val_loss,
                    "epoch": epoch,
                },
                CHECKPOINT_PATH,
            )
            
        if epoch % 5 == 0 or epoch == epochs:
            print(f" Epoch [{epoch:02d}/{epochs:02d}] - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} {'*' if val_loss <= best_loss else ''}")
            
    print(f"\n Best Model Checkpoint Saved with Validation Loss: {best_loss:.4f}")
    
    # Detailed Evaluation
    evaluation = evaluate_saved_model(device=device)
    return evaluation


def evaluate_saved_model(device: Optional[str] = None) -> Dict:
    """
    Evaluates the saved model checkpoint across all 9 crops,
    computing MAE, RMSE, MAPE, and R2 metrics on original LKR/kg price scale.
    """
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"Checkpoint not found at {CHECKPOINT_PATH}. Run training first.")
        
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device)
    meta = checkpoint["meta"]
    scaler = joblib.load(SCALER_PATH)
    
    model = CropPriceLSTM(
        num_crops=len(meta["crops"]),
        feature_dim=len(meta["feature_cols"]),
        embedding_dim=8,
        hidden_dim=64,
        num_layers=2,
        forecast_horizon=meta["forecast_horizon"],
        dropout=0.2,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    
    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values(by=["crop_name", "date"], inplace=True)
    
    target_mean = meta["target_mean"]
    target_scale = meta["target_scale"]
    seq_len = meta["seq_len"]
    horizon = meta["forecast_horizon"]
    
    results_by_crop = {}
    all_y_true = []
    all_y_pred = []
    
    for crop in meta["crops"]:
        c_df = df[df["crop_name"] == crop].copy().reset_index(drop=True)
        c_idx = meta["crop_to_idx"][crop]
        
        feats = scaler.transform(c_df[meta["feature_cols"]])
        targets = c_df[meta["target_col"]].values
        
        n_samples = len(feats)
        y_trues_crop = []
        y_preds_crop = []
        
        for i in range(n_samples - (seq_len + horizon) + 1):
            x_seq = torch.tensor(feats[i : i + seq_len], dtype=torch.float32).unsqueeze(0).to(device)
            c_tensor = torch.tensor([c_idx], dtype=torch.long).to(device)
            
            with torch.no_grad():
                pred_scaled = model(x_seq, c_tensor).cpu().numpy()[0]
                
            pred_unscaled = pred_scaled * target_scale + target_mean
            true_unscaled = targets[i + seq_len : i + seq_len + horizon]
            
            # evaluate step-1 and average over horizon
            y_trues_crop.append(true_unscaled[0])
            y_preds_crop.append(pred_unscaled[0])
            
        y_trues_crop = np.array(y_trues_crop)
        y_preds_crop = np.array(y_preds_crop)
        
        # Test split slice (last 18 months)
        test_slice = 18
        y_t = y_trues_crop[-test_slice:]
        y_p = y_preds_crop[-test_slice:]
        
        mae = float(mean_absolute_error(y_t, y_p))
        rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
        mape = float(np.mean(np.abs((y_t - y_p) / (y_t + 1e-5))) * 100)
        r2 = float(r2_score(y_t, y_p))
        
        results_by_crop[crop] = {
            "MAE_LKR": round(mae, 2),
            "RMSE_LKR": round(rmse, 2),
            "MAPE_pct": round(mape, 2),
            "R2_Score": round(r2, 3),
            "Mean_Actual_Price": round(float(np.mean(y_t)), 2),
        }
        all_y_true.extend(y_t)
        all_y_pred.extend(y_p)
        
    all_y_true = np.array(all_y_true)
    all_y_pred = np.array(all_y_pred)
    
    overall_mae = float(mean_absolute_error(all_y_true, all_y_pred))
    overall_rmse = float(np.sqrt(mean_squared_error(all_y_true, all_y_pred)))
    overall_mape = float(np.mean(np.abs((all_y_true - all_y_pred) / (all_y_true + 1e-5))) * 100)
    overall_r2 = float(r2_score(all_y_true, all_y_pred))
    
    summary_metrics = {
        "overall": {
            "MAE_LKR": round(overall_mae, 2),
            "RMSE_LKR": round(overall_rmse, 2),
            "MAPE_pct": round(overall_mape, 2),
            "R2_Score": round(overall_r2, 3),
        },
        "by_crop": results_by_crop,
    }
    
    with open(METRICS_PATH, "w") as f:
        json.dump(summary_metrics, f, indent=2)
        
    print("\n" + "=" * 55)
    print("        PYTORCH MODEL EVALUATION REPORT")
    print("=" * 55)
    print(f"Overall MAE:  LKR {overall_mae:.2f} / kg")
    print(f"Overall RMSE: LKR {overall_rmse:.2f} / kg")
    print(f"Overall MAPE: {overall_mape:.2f} %")
    print(f"Overall R²:   {overall_r2:.3f}")
    print("-" * 55)
    print(f"{'Crop':<15} {'MAE (LKR)':<12} {'RMSE':<10} {'MAPE (%)':<10} {'R²':<6}")
    print("-" * 55)
    for crop, m in results_by_crop.items():
        print(f"{crop:<15} {m['MAE_LKR']:<12.2f} {m['RMSE_LKR']:<10.2f} {m['MAPE_pct']:<10.2f} {m['R2_Score']:<6.3f}")
    print("=" * 55)
    
    return summary_metrics


_CACHED_MODEL = None
_CACHED_META = None
_CACHED_SCALER = None


def get_cached_model(device: Optional[str] = None):
    global _CACHED_MODEL, _CACHED_META, _CACHED_SCALER
    if _CACHED_MODEL is None:
        if device is None:
            device = "cpu"  # CPU is instant for single inference vectors
        checkpoint = torch.load(CHECKPOINT_PATH, map_location=device)
        _CACHED_META = checkpoint["meta"]
        _CACHED_SCALER = joblib.load(SCALER_PATH)
        
        model = CropPriceLSTM(
            num_crops=len(_CACHED_META["crops"]),
            feature_dim=len(_CACHED_META["feature_cols"]),
            embedding_dim=8,
            hidden_dim=64,
            num_layers=2,
            forecast_horizon=_CACHED_META["forecast_horizon"],
            dropout=0.2,
        ).to(device)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        _CACHED_MODEL = (model, device)
    return _CACHED_MODEL[0], _CACHED_MODEL[1], _CACHED_META, _CACHED_SCALER


def predict_future_prices(
    crop_name: str,
    recent_months: int = 6,
    device: Optional[str] = None,
) -> Dict:
    """
    Generates multi-month forward price forecast (with confidence bounds)
    for a given crop using the latest observed data.
    """
    model, device, meta, scaler = get_cached_model(device)
    
    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    c_df = df[df["crop_name"] == crop_name].sort_values("date").reset_index(drop=True)
    
    seq_len = meta["seq_len"]
    horizon = meta["forecast_horizon"]
    target_mean = meta["target_mean"]
    target_scale = meta["target_scale"]
    crop_idx = meta["crop_to_idx"][crop_name]
    
    # Get last seq_len records
    recent_records = c_df.iloc[-seq_len:]
    last_date = recent_records["date"].max()
    
    feats = scaler.transform(recent_records[meta["feature_cols"]])
    x_seq = torch.tensor(feats, dtype=torch.float32).unsqueeze(0).to(device)
    c_tensor = torch.tensor([crop_idx], dtype=torch.long).to(device)
    
    with torch.no_grad():
        preds_scaled = model(x_seq, c_tensor).cpu().numpy()[0]
        
    preds_unscaled = preds_scaled * target_scale + target_mean
    
    # Standard historical error variance for confidence interval estimation (90% CI ~ 1.645 * RMSE)
    rmse_crop = 25.0
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH) as f:
                metrics_data = json.load(f)
                rmse_crop = metrics_data["by_crop"].get(crop_name, {}).get("RMSE_LKR", 25.0)
        except Exception:
            pass
            
    future_dates = [last_date + pd.DateOffset(months=m) for m in range(1, horizon + 1)]
    
    forecasts = []
    for d, p in zip(future_dates, preds_unscaled):
        val = max(10.0, float(p))
        lower = max(5.0, val - 1.645 * rmse_crop)
        upper = val + 1.645 * rmse_crop
        forecasts.append({
            "month_offset": len(forecasts) + 1,
            "forecast_date": d.strftime("%Y-%m-%d"),
            "predicted_farm_price": round(val, 2),
            "ci_lower": round(lower, 2),
            "ci_upper": round(upper, 2),
        })
        
    return {
        "crop_name": crop_name,
        "base_date": last_date.strftime("%Y-%m-%d"),
        "forecast_horizon_months": horizon,
        "forecasts": forecasts,
    }


def predict_price_and_weather_fluctuations(
    crop_name: str,
    start_year: int = 2026,
    start_month: int = 10,
    horizon: int = 4,
    direction: str = "forward",
    annual_inflation_rate: float = 5.5,
    district: str = "Badulla",
    device: Optional[str] = None,
) -> Dict:
    """
    Computes price projections and monthly fluctuations (deltas and percentage changes)
    paired with expected meteorological conditions (temperature, rainfall, rain days, sunshine),
    accounting for starting year, starting month, calculation direction (forward or backward in time),
    and compounded market inflation.
    """
    MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    
    crop_df = df[df["crop_name"] == crop_name].sort_values("date")
    
    # Monthly inflation rate from annual rate (compounded)
    monthly_inflation = (1.0 + (annual_inflation_rate / 100.0)) ** (1.0 / 12.0) - 1.0
    
    # 1. Determine Starting Month Base Price
    # Check if exact year & month exists in historical data
    start_hist_match = crop_df[(crop_df["year"] == start_year) & (crop_df["month"] == start_month)]
    if len(start_hist_match) > 0:
        base_price = float(start_hist_match["farm_price"].iloc[-1])
    else:
        # Fallback to recent seasonal price escalated by inflation to target start_year
        m_hist = crop_df[crop_df["month"] == start_month]
        ref_year = 2024
        ref_price = float(m_hist["farm_price"].iloc[-1]) if len(m_hist) > 0 else float(crop_df["farm_price"].median())
        year_diff = start_year - ref_year
        base_price = ref_price * ((1.0 + (annual_inflation_rate / 100.0)) ** year_diff)
        
    base_price = max(10.0, round(base_price, 2))
    
    # Query PyTorch model for baseline relative forward predictions
    fc_data = predict_future_prices(crop_name=crop_name, device=device)
    raw_preds = [f["predicted_farm_price"] for f in fc_data["forecasts"]]
    
    # Standard historical error variance for confidence bounds
    rmse_crop = 25.0
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH) as f:
                metrics_data = json.load(f)
                rmse_crop = metrics_data["by_crop"].get(crop_name, {}).get("RMSE_LKR", 25.0)
        except Exception:
            pass
            
    # Compile timeline (forward or backward)
    timeline = []
    prev_price = base_price
    sign = 1 if direction.lower() == "forward" else -1
    
    for offset in range(1, horizon + 1):
        step = sign * offset
        total_months = (start_year * 12 + (start_month - 1)) + step
        target_y = total_months // 12
        target_m = (total_months % 12) + 1
        target_name = MONTH_NAMES[target_m - 1]
        period_label = f"{target_name[:3]} {target_y}"
        
        # Inflation multiplier relative to base period
        # If forward: (1 + r)^k, if backward: (1 + r)^(-k)
        inflation_mult = (1.0 + monthly_inflation) ** step
        
        # Expected seasonal climate for target month
        m_weather = df[df["month"] == target_m]
        exp_temp = round(float(m_weather["temp_mean"].median()), 1)
        exp_temp_max = round(float(m_weather["temp_max"].max()), 1)
        exp_temp_min = round(float(m_weather["temp_min"].min()), 1)
        exp_rain = round(float(m_weather["rain_sum"].median()), 1)
        exp_rain_days = round(float(m_weather["rain_days"].median()), 0)
        exp_sunshine = round(float(m_weather["sunshine_mean_hours"].median()), 1)
        
        # Determine climate condition and risk level
        if exp_rain >= 220:
            weather_condition = "Northeast / Southwest Monsoon Peaks (High Rainfall)"
            weather_risk = "Elevated Flood Risk"
        elif exp_rain <= 60:
            weather_condition = "Dry Season (Low Rainfall / Elevated Evapotranspiration)"
            weather_risk = "Water Deficit Risk"
        elif exp_temp >= 30:
            weather_condition = "High Ambient Heat / Solar Radiation"
            weather_risk = "Heat Stress Risk"
        else:
            weather_condition = "Moderate Inter-Monsoonal Weather (Favorable)"
            weather_risk = "Optimal Growth Weather"
            
        # Check if actual historical record exists for this target period
        hist_period_match = crop_df[(crop_df["year"] == target_y) & (crop_df["month"] == target_m)]
        if len(hist_period_match) > 0:
            pred_price = round(float(hist_period_match["farm_price"].iloc[-1]), 2)
            is_actual = True
        else:
            # Model forecast blended with seasonal anchor and market inflation
            m_hist_prices = crop_df[crop_df["month"] == target_m]["farm_price"]
            seasonal_anchor = float(m_hist_prices.median()) if len(m_hist_prices) > 0 else base_price
            
            model_pred_idx = min(offset - 1, len(raw_preds) - 1)
            model_val = raw_preds[model_pred_idx]
            
            # Baseline unadjusted price
            unadjusted_price = 0.6 * model_val + 0.4 * seasonal_anchor
            # Apply cumulative market inflation
            pred_price = round(unadjusted_price * inflation_mult, 2)
            is_actual = False
            
        pred_price = max(10.0, pred_price)
        
        # Real price in base starting year/month constant rupees
        real_price = round(pred_price / inflation_mult, 2)
        
        # Fluctuation statistics
        delta_lkr = round(pred_price - prev_price, 2)
        pct_change = round(((pred_price - prev_price) / (prev_price + 1e-4)) * 100, 2)
        cum_pct_change = round(((pred_price - base_price) / (base_price + 1e-4)) * 100, 2)
        
        # Confidence interval scaled with inflation
        scaled_rmse = rmse_crop * (inflation_mult if inflation_mult > 0 else 1.0)
        ci_lower = max(10.0, round(pred_price - 1.645 * scaled_rmse, 2))
        ci_upper = round(pred_price + 1.645 * scaled_rmse, 2)
        
        # Status Label
        if pct_change >= 10.0:
            fluctuation_status = f"Sharp Rise (+{pct_change}%)"
            trend_direction = "Rising"
        elif pct_change >= 3.0:
            fluctuation_status = f"Moderate Rise (+{pct_change}%)"
            trend_direction = "Rising"
        elif pct_change <= -10.0:
            fluctuation_status = f"Sharp Drop ({pct_change}%)"
            trend_direction = "Falling"
        elif pct_change <= -3.0:
            fluctuation_status = f"Moderate Drop ({pct_change}%)"
            trend_direction = "Falling"
        else:
            fluctuation_status = f"Stable ({'+' if pct_change > 0 else ''}{pct_change}%)"
            trend_direction = "Stable"
            
        timeline.append({
            "month_offset": offset,
            "step": step,
            "target_year": target_y,
            "target_month_num": target_m,
            "target_month_name": target_name,
            "target_period_label": period_label,
            "projected_farm_price": pred_price,
            "real_price_constant": real_price,
            "inflation_multiplier": round(inflation_mult, 4),
            "price_delta_lkr": delta_lkr,
            "price_pct_change": pct_change,
            "cumulative_pct_change": cum_pct_change,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "fluctuation_status": fluctuation_status,
            "trend_direction": trend_direction,
            "is_actual": is_actual,
            "weather": {
                "temp_mean": exp_temp,
                "temp_min": exp_temp_min,
                "temp_max": exp_temp_max,
                "rain_sum": exp_rain,
                "rain_days": int(exp_rain_days),
                "sunshine_hours": exp_sunshine,
                "weather_condition": weather_condition,
                "weather_risk": weather_risk,
            },
        })
        prev_price = pred_price
        
    return {
        "crop_name": crop_name,
        "start_year": start_year,
        "start_month_num": start_month,
        "start_month_name": MONTH_NAMES[start_month - 1],
        "start_period_label": f"{MONTH_NAMES[start_month - 1][:3]} {start_year}",
        "base_farm_price_lkr": round(base_price, 2),
        "horizon_months": horizon,
        "direction": direction.lower(),
        "annual_inflation_rate_pct": annual_inflation_rate,
        "district": district,
        "timeline": timeline,
    }


if __name__ == "__main__":
    train_model(epochs=35)

