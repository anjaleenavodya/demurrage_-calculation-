# Sri Lanka Agri-MIS: End-to-End Execution Guide

A simplified, step-by-step guide explaining the complete data pipeline, sequence modeling, plantation decision engine, and Streamlit web dashboard.

---

## 1. System Overview

The system bridges three data sources to give smallholder farmers and agricultural analysts forward-looking price predictions and crop planting advice:

```
[Raw Data Sources]
  1. Historical Vegetable Prices (2000 - 2025, 9 crops)
  2. National Daily Weather Records (2010 - 2024, 27 meteorological stations)
  3. Smallholder Farmer Survey (Badulla & Welimada)
          |
          v
[Data Preprocessing & Database Engine] (src/data_preprocessing.py)
  - Daily weather aggregated to monthly statistics
  - Cyclical month encodings and price lag features engineered
  - Sinhala survey translated to English and semantically grouped
  - Relational SQLite database populated (data_processed/agriculture_mis.db)
          |
          v
[PyTorch Sequence Deep Learning Model] (src/model_pytorch.py)
  - Bidirectional LSTM with Crop Entity Embeddings and Temporal Attention
  - Sliding window: 6 months of historical sequence predicting 1-to-12 months forward
  - Forward/backward inflation compounding and 90% confidence corridor calculation
          |
          v
[Plantation Recommendation Engine] (src/recommendation_engine.py)
  - Crop gestation matching (2 - 4 months)
  - Agro-climatic suitability scoring (temperature & rainfall tolerances)
  - Net profit margin calculation per acre
          |
          v
[Interactive Streamlit Dashboard] (src/app.py)
  - Executive Overview
  - Farmer Survey Insights
  - Price & Weather Analytics
  - PyTorch Forecast & Fluctuation (Year, forward/backward, inflation)
  - Smart Crop Plantation Advisor
```

---

## 2. Environment Setup

Always use the project's dedicated Python virtual environment located in `.venv`.

### Activate the Virtual Environment

On macOS / Linux:
```bash
cd /Users/nushan/Projects/Anjalee/Final
source .venv/bin/activate
```

Alternatively, invoke Python directly using the virtual environment path:
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python <script_name>.py
```

### Virtual Environment Packages
All required packages (`torch`, `pandas`, `numpy`, `scikit-learn`, `streamlit`, `plotly`, `joblib`) are pre-installed. To verify:
```bash
.venv/bin/python -c "import torch, streamlit, plotly, sklearn; print('Environment is ready!')"
```

---

## 3. Step 1: Data Preprocessing and Database Creation

### What This Step Does
1. **Weather Aggregation**: Reads 142,371 daily meteorological records from 27 stations and aggregates them into monthly metrics:
   - Average, maximum, and minimum ambient temperature (Celsius).
   - Monthly cumulative rainfall (mm) and rainy day count.
   - Bright sunshine duration and FAO reference evapotranspiration (et0).
2. **Price Feature Engineering**: Aligns monthly crop prices with weather variables, adds 1-month and 2-month price lags, cyclical month encodings (`month_sin`, `month_cos`), and wholesale-retail intermediary price spreads.
3. **Farmer Survey Translation & Semantic Grouping**: Translates raw Sinhala responses from Badulla and Welimada smallholders into standardized English and groups related concepts (e.g. experience tiers, farm sizes, causes of volatility).
4. **SQLite Database Storage**: Creates indexed relational tables in `data_processed/agriculture_mis.db`.

### How to Run Preprocessing

Command:
```bash
.venv/bin/python main.py --preprocess
```

Or run the script directly:
```bash
.venv/bin/python src/data_preprocessing.py
```

### Sample Python Code: Querying the Processed Database
```python
import sqlite3
import pandas as pd

# Connect to the SQLite database
conn = sqlite3.connect("data_processed/agriculture_mis.db")

# Query monthly average farm prices for Carrot alongside rainfall
query = """
SELECT crop_name, date, farm_price, rain_sum, temp_mean
FROM crop_weather_monthly
WHERE crop_name = 'Carrot' AND year >= 2023
ORDER BY date ASC
LIMIT 5;
"""
df = pd.read_sql_query(query, conn)
print(df)
conn.close()
```

---

## 4. Step 2: PyTorch Deep Learning Model Training

### Model Architecture
- **Input Tensor**: Sequence length of 6 consecutive months with 15 continuous variables (prices, lags, spreads, rainfall, temperature, solar radiation) plus an 8-dimensional learnable Crop Entity Embedding.
- **Backbone**: 2-layer Stacked Bidirectional LSTM (hidden dimension: 64).
- **Attention Layer**: Temporal Attention mechanism that assigns dynamic importance weights to the historical months.
- **Output Head**: Multi-horizon linear projector predicting future farmgate prices.

### How to Train the Model

Command:
```bash
.venv/bin/python main.py --train --epochs 35
```

Or run the training script directly:
```bash
.venv/bin/python src/model_pytorch.py
```

### Training Outputs
- Model checkpoint weights: `models/pytorch_crop_lstm.pt`
- Feature normalization scaler: `models/feature_scaler.joblib`
- Out-of-sample evaluation metrics: `models/model_metrics.json`

---

## 5. Step 3: Model Evaluation and Accuracy Inspection

### How to Evaluate the Model

Command:
```bash
.venv/bin/python main.py --evaluate
```

### Sample Metrics on Hold-Out Test Data (2023 - 2024)

| Crop Name | Mean Actual Price | MAE (LKR/kg) | RMSE (LKR/kg) | MAPE (%) |
| :--- | :--- | :--- | :--- | :--- |
| **Beans** | LKR 212.65 | 45.32 | 61.88 | 18.51 % |
| **Brinjal** | LKR 178.90 | 33.10 | 42.91 | 16.69 % |
| **Cabbage** | LKR 185.40 | 35.31 | 47.10 | 16.65 % |
| **Carrot** | LKR 245.80 | 68.01 | 84.22 | 24.36 % |
| **Green Chilli** | LKR 310.50 | 89.98 | 110.29 | 27.95 % |
| **Lime** | LKR 340.20 | 123.20 | 143.48 | 31.87 % |
| **Pumpkin** | LKR 115.30 | 19.14 | 22.20 | 14.88 % |
| **Snake Gourd** | LKR 125.75 | 25.49 | 30.47 | 18.86 % |
| **Tomato** | LKR 230.10 | 56.82 | 71.48 | 21.93 % |
| **OVERALL** | **LKR 216.07** | **LKR 55.15** | **LKR 77.65** | **21.30 %** |

---

## 6. Step 4: Price Fluctuation and Inflation Forecasting

The function `predict_price_and_weather_fluctuations` enables forward and backward price simulations with market inflation compounding.

### Sample Code: Running a Simulation in Python
```python
from src.model_pytorch import predict_price_and_weather_fluctuations

# Simulate forward 4 months starting from October 2026 with 5.5% annual inflation
results = predict_price_and_weather_fluctuations(
    crop_name="Carrot",
    start_year=2026,
    start_month=10,
    horizon=4,
    direction="forward",
    annual_inflation_rate=5.5,
    district="Badulla",
)

print(f"Crop: {results['crop_name']}")
print(f"Base Period: {results['start_period_label']} | Base Price: LKR {results['base_farm_price_lkr']:.2f}")

for step in results["timeline"]:
    period = step["target_period_label"]
    nom_price = step["projected_farm_price"]
    real_price = step["real_price_constant"]
    status = step["fluctuation_status"]
    rain = step["weather"]["rain_sum"]
    temp = step["weather"]["temp_mean"]
    print(f"  {period}: Nom LKR {nom_price:.2f} | Real LKR {real_price:.2f} | Fluctuation: {status} | Rain: {rain}mm | Temp: {temp}C")
```

### Sample Output:
```
Crop: Carrot
Base Period: Oct 2026 | Base Price: LKR 333.33
  Nov 2026: Nom LKR 178.05 | Real LKR 177.26 | Fluctuation: Sharp Drop (-46.58%) | Rain: 315.4mm | Temp: 24.6C
  Dec 2026: Nom LKR 182.50 | Real LKR 180.88 | Fluctuation: Stable (+2.50%)     | Rain: 218.9mm | Temp: 24.3C
  Jan 2027: Nom LKR 187.10 | Real LKR 184.61 | Fluctuation: Stable (+2.52%)     | Rain: 79.4mm  | Temp: 24.1C
  Feb 2027: Nom LKR 189.75 | Real LKR 186.35 | Fluctuation: Stable (+1.42%)     | Rain: 73.1mm  | Temp: 24.7C
```

---

## 7. Step 5: Crop Plantation Recommendation Engine

### How It Works
1. Smallholder selects: **Planting Month**, **Farm Size (Acres)**, and **District**.
2. For each of the 9 crops, the engine:
   - Identifies the harvest month: `Harvest Month = (Planting Month + Gestation Months - 1) % 12 + 1`.
   - Projects the expected farmgate harvest price using the sequence model.
   - Evaluates agro-climatic suitability: compares historical temperature and rainfall in the district against Department of Agriculture physiological thresholds.
   - Computes estimated total production costs, expected gross revenue, and net profit margin.
   - Generates a composite score (0 - 100) and recommendation verdict.

### How to Run the Recommendation Engine via CLI

Command:
```bash
.venv/bin/python main.py --recommend --month 10 --district Badulla
```

### Sample Python Code:
```python
from src.recommendation_engine import recommend_crops

# Recommend best crops for planting in October (Maha season) on 1.5 acres in Badulla
recommendations = recommend_crops(
    planting_month=10,
    farm_size_acres=1.5,
    target_district="Badulla",
    risk_preference="Balanced",
)

# Print Top 3 ranked crops
for rec in recommendations[:3]:
    print(f"Rank #{rec['rank']}: {rec['crop_name']} ({rec['verdict']})")
    print(f"  Harvest Month: {rec['harvest_month_name']} (Cycle: {rec['gestation_months']} months)")
    print(f"  Predicted Price: LKR {rec['predicted_farm_price_lkr']:.2f} / kg")
    print(f"  Projected Net Profit: LKR {rec['projected_net_profit_total_lkr']:,.0f}")
    print(f"  Climate Match: {rec['climate_suitability_score']}%")
    print(f"  Tip: {rec['agronomic_tip']}\n")
```

---

## 8. Step 6: Interactive Streamlit Web Application

The interactive web dashboard provides a complete user interface for smallholders, researchers, and extension officers.

### How to Launch the Web App

Command:
```bash
.venv/bin/python main.py --app
```

Or directly with Streamlit:
```bash
.venv/bin/streamlit run src/app.py
```

Access the dashboard in your web browser:
```
http://localhost:8501
```

### Dashboard Modules Breakdown

1. **Executive Overview**:
   - System KPIs: 9 commercial crops, 2,772 price records, 142k weather rows, 100% farmer survey validation.
   - Problem statement, research objectives, and crop agronomic profiles table.
2. **Farmer Survey Insights**:
   - Badulla and Welimada smallholder farmer empirical survey analysis.
   - Interactive charts: experience tiers, primary causes of price volatility, farm size categories, and information sources.
   - Clean, 100% English respondent profiles table with semantic groupings.
3. **Price & Weather Analytics**:
   - Historical time-series charts (2000 - 2025) comparing farmgate prices, Pettah wholesale prices, Dambulla Dedicated Economic Centre prices, and intermediary spread margins.
   - Monthly seasonal distributions and national climate curves.
   - Cross-correlation heatmap between meteorological variables and commodity prices.
4. **PyTorch Forecast & Fluctuation**:
   - Select Commodity Crop, Starting Year (2000 - 2035), Starting Month, and Agricultural District.
   - Select Calculation Direction: Forward in time (Future Forecast) or Backwards in time (Historical Analysis).
   - Adjust Annual Market Inflation Rate (%) and Forecast Horizon (1 - 12 months).
   - Interactive dual-axis charts: Nominal Price curve with 90% confidence corridor, Real Constant Price curve, and step fluctuation bars.
   - Expected rainfall and temperature progression charts.
   - Complete month-by-month schedule matrix table.
5. **Crop Plantation Advisor**:
   - Interactive farmer inputs: Planting Month, District, Farm Acreage, and Risk Preference.
   - Top 3 crop recommendation cards with scores, harvest months, projected profit, and agronomic tips.
   - Complete 9-crop comparative matrix and CSV export download button.

---

## 9. Step 7: Unified CLI Orchestrator (`main.py`)

The root file `main.py` provides an interactive terminal menu and command-line flags.

### Launch Interactive Menu
```bash
.venv/bin/python main.py
```

Menu Options:
```
============================================================
  SRI LANKA AGRI-MIS: PRICE FORECAST & CROP ADVISOR
============================================================
  [1] Preprocess Data & Build SQLite Database
  [2] Train PyTorch BiLSTM Sequence Model
  [3] Evaluate Saved Model & Display Metrics
  [4] Run Crop Plantation Recommendation Engine
  [5] Launch Streamlit Interactive Web Application
  [6] Run Full End-to-End Pipeline & Launch App
  [0] Exit
============================================================
```

### Command-Line Arguments Reference

| Action | Terminal Command |
| :--- | :--- |
| **Run Everything End-to-End** | `.venv/bin/python main.py --all` |
| **Run Preprocessing Only** | `.venv/bin/python main.py --preprocess` |
| **Train Sequence Model** | `.venv/bin/python main.py --train --epochs 35` |
| **Evaluate Model Accuracy** | `.venv/bin/python main.py --evaluate` |
| **Run Crop Advisor** | `.venv/bin/python main.py --recommend --month 10 --district Badulla` |
| **Start Web Application** | `.venv/bin/python main.py --app` |

---

## 10. Frequently Asked Questions & Troubleshooting

### Port 8501 is already in use
If port 8501 is occupied by another process, specify a custom port:
```bash
.venv/bin/streamlit run src/app.py --server.port 8502
```

### Missing Database File
If `data_processed/agriculture_mis.db` is missing, rebuild it by running:
```bash
.venv/bin/python main.py --preprocess
```

### How to Adjust the Inflation Compounding
In the Streamlit web dashboard under **PyTorch Forecast & Fluctuation**, change the **Annual Inflation Rate (%)** input (default is `5.5%`). The model recalculates the monthly multiplier $(1 + r_{\text{month}})^k$ dynamically.

### How to Change the Forecast Horizon
Adjust the slider in the web app (1 to 12 months forward or backward) to simulate planting seasons (e.g., 4 months for Maha season or 3 months for short-duration crops like Cabbage and Beans).
