"""
Power BI Integration & Export Module
Generates standardized star-schema tables (fact and dimension CSVs),
executable Power BI Python script connector, and comprehensive DAX guides.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.model_pytorch import predict_future_prices
from src.recommendation_engine import recommend_crops, CROP_AGRONOMIC_PROFILES

EXPORTS_DIR = os.path.join(PROJECT_ROOT, "exports_powerbi")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data_processed")


def generate_powerbi_tables():
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    
    print(" Generating Power BI Star-Schema Export Tables...")
    
    # 1. Fact: Historical Crop Prices
    prices_raw = pd.read_csv(os.path.join(PROCESSED_DIR, "crop_prices_clean.csv"))
    fact_prices = prices_raw[[
        "date", "year", "month", "crop_name", "farm_price",
        "retail_price_pettah", "retail_price_dambulla", "average_spread", "spread_pct"
    ]].copy()
    fact_prices.to_csv(os.path.join(EXPORTS_DIR, "fact_historical_prices.csv"), index=False)
    print(f"  -> {len(fact_prices)} rows written to fact_historical_prices.csv")
    
    # 2. Fact: Monthly Weather
    weather_raw = pd.read_csv(os.path.join(PROCESSED_DIR, "weather_monthly_national.csv"))
    fact_weather = weather_raw[[
        "date", "year", "month", "temp_mean", "temp_max", "temp_min",
        "rain_sum", "rain_days", "sunshine_mean_hours", "radiation_mean", "et0_mean", "wind_speed_max"
    ]].copy()
    fact_weather.to_csv(os.path.join(EXPORTS_DIR, "fact_monthly_weather.csv"), index=False)
    print(f"  -> {len(fact_weather)} rows written to fact_monthly_weather.csv")
    
    # 3. Fact: PyTorch Model Forecasts
    forecast_rows = []
    crops = sorted(prices_raw["crop_name"].unique())
    for crop in crops:
        try:
            fc = predict_future_prices(crop)
            for f in fc["forecasts"]:
                forecast_rows.append({
                    "crop_name": crop,
                    "base_date": fc["base_date"],
                    "forecast_date": f["forecast_date"],
                    "month_offset": f["month_offset"],
                    "predicted_farm_price": f["predicted_farm_price"],
                    "ci_lower": f["ci_lower"],
                    "ci_upper": f["ci_upper"],
                    "model_type": "PyTorch BiLSTM-Attention",
                })
        except Exception as e:
            print(f"Warning: could not generate forecast for {crop}: {e}")
            
    fact_forecasts = pd.DataFrame(forecast_rows)
    fact_forecasts.to_csv(os.path.join(EXPORTS_DIR, "fact_model_forecasts.csv"), index=False)
    print(f"  -> {len(fact_forecasts)} rows written to fact_model_forecasts.csv")
    
    # 4. Fact: Crop Recommendations Matrix (All 12 Months x Key Districts)
    sample_districts = ["Badulla", "Nuwara Eliya", "Matale", "Anuradhapura"]
    recs_rows = []
    for month in range(1, 13):
        for dist in sample_districts:
            recs = recommend_crops(planting_month=month, farm_size_acres=1.0, target_district=dist)
            for r in recs:
                recs_rows.append({
                    "planting_month_num": month,
                    "planting_month_name": r["planting_month_name"],
                    "district": dist,
                    "crop_name": r["crop_name"],
                    "rank": r["rank"],
                    "recommendation_score": r["recommendation_score"],
                    "verdict": r["verdict"],
                    "harvest_month_name": r["harvest_month_name"],
                    "gestation_months": r["gestation_months"],
                    "predicted_farm_price_lkr": r["predicted_farm_price_lkr"],
                    "production_cost_per_kg_lkr": r["production_cost_per_kg_lkr"],
                    "net_margin_per_kg_lkr": r["net_margin_per_kg_lkr"],
                    "profit_margin_pct": r["profit_margin_pct"],
                    "climate_suitability_score": r["climate_suitability_score"],
                })
    fact_recs = pd.DataFrame(recs_rows)
    fact_recs.to_csv(os.path.join(EXPORTS_DIR, "fact_crop_recommendations.csv"), index=False)
    print(f"  -> {len(fact_recs)} rows written to fact_crop_recommendations.csv")
    
    # 5. Dim: Crop Profiles
    crop_dim_rows = []
    for c, p in CROP_AGRONOMIC_PROFILES.items():
        crop_dim_rows.append({
            "crop_name": c,
            "duration_months": p["duration_months"],
            "ideal_temp_min": p["ideal_temp_min"],
            "ideal_temp_max": p["ideal_temp_max"],
            "ideal_rain_min": p["ideal_rain_min"],
            "ideal_rain_max": p["ideal_rain_max"],
            "flood_sensitivity": p["flood_sensitivity"],
            "drought_tolerance": p["drought_tolerance"],
            "est_cost_per_kg": p["est_cost_per_kg"],
            "yield_per_acre_kg": p["yield_per_acre_kg"],
            "primary_zones": ", ".join(p["primary_zones"]),
            "agronomic_tip": p["agronomic_tip"],
        })
    dim_crops = pd.DataFrame(crop_dim_rows)
    dim_crops.to_csv(os.path.join(EXPORTS_DIR, "dim_crops.csv"), index=False)
    print(f"  -> {len(dim_crops)} rows written to dim_crops.csv")
    
    # 6. Dim: Farmer Survey
    survey_clean = pd.read_csv(os.path.join(PROCESSED_DIR, "farmer_survey_cleaned.csv"))
    survey_clean.to_csv(os.path.join(EXPORTS_DIR, "dim_farmer_survey.csv"), index=False)
    print(f"  -> {len(survey_clean)} rows written to dim_farmer_survey.csv")
    
    # 7. Generate Python script connector for Power BI Desktop
    create_powerbi_python_script()
    create_powerbi_markdown_guide()
    
    print("\n Power BI Data Package Generated Successfully in: exports_powerbi/")


def create_powerbi_python_script():
    script_path = os.path.join(EXPORTS_DIR, "powerbi_live_data_connector.py")
    script_content = f'''# ==============================================================================
# Power BI Desktop Python Script Data Connector
# Usage:
#   1. In Power BI Desktop, click "Get Data" -> "More..." -> "Python script"
#   2. Copy and paste this script into the prompt and click OK.
# ==============================================================================

import pandas as pd
import os

EXPORTS_DIR = r"{EXPORTS_DIR}"

# Load Star-Schema tables into Power BI Data Model
fact_prices = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_historical_prices.csv"))
fact_weather = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_monthly_weather.csv"))
fact_forecasts = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_model_forecasts.csv"))
fact_crop_recommendations = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_crop_recommendations.csv"))
dim_crops = pd.read_csv(os.path.join(EXPORTS_DIR, "dim_crops.csv"))
dim_farmer_survey = pd.read_csv(os.path.join(EXPORTS_DIR, "dim_farmer_survey.csv"))
'''
    with open(script_path, "w") as f:
        f.write(script_content)


def create_powerbi_markdown_guide():
    guide_path = os.path.join(EXPORTS_DIR, "POWERBI_SETUP_GUIDE.md")
    guide_content = """# Power BI Dashboard Setup & Integration Guide

This guide explains how to connect and build an interactive executive dashboard in **Power BI Desktop** using the processed datasets and PyTorch model predictions.

---

## 1. Connecting Data to Power BI Desktop

### Option A: Direct CSV Import (Recommended)
1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Folder** (or **Text/CSV**).
3. Select the folder path: `exports_powerbi/`.
4. Power BI will load all tables:
   - `fact_historical_prices`: Monthly actual prices (farmgate, Pettah, Dambulla) and spreads (2000-2025).
   - `fact_monthly_weather`: Aggregated national climate indicators (temp, rainfall, sunshine, evapotranspiration).
   - `fact_model_forecasts`: PyTorch multi-horizon predicted prices with 90% confidence bounds.
   - `fact_crop_recommendations`: Cultivation recommendations for all 12 planting months and districts.
   - `dim_crops`: Agronomic profiles, gestation periods, and temperature/rainfall thresholds.
   - `dim_farmer_survey`: Survey analytics from Badulla & Welimada smallholder farmers.

### Option B: Native Python Script Connector
1. In Power BI Desktop, click **Get Data** -> **More...** -> **Python script**.
2. Open `exports_powerbi/powerbi_live_data_connector.py`, paste its contents, and click **OK**.
3. Select all loaded tables and click **Load**.

---

## 2. Power BI Data Model (Star Schema Relationships)

Create the following relationships in the **Model View**:

| From Table | Column | To Table | Column | Cardinality | Cross Filter |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fact_historical_prices` | `crop_name` | `dim_crops` | `crop_name` | Many to One (*:1) | Single |
| `fact_model_forecasts` | `crop_name` | `dim_crops` | `crop_name` | Many to One (*:1) | Single |
| `fact_crop_recommendations` | `crop_name` | `dim_crops` | `crop_name` | Many to One (*:1) | Single |
| `fact_historical_prices` | `date` | `fact_monthly_weather`| `date` | Many to Many (*:*) | Both |

---

## 3. Essential DAX Measures

Add these DAX measures to your Power BI report:

```dax
// 1. Average Farmgate Price
Avg Farm Price = AVERAGE(fact_historical_prices[farm_price])

// 2. Average Retail Pettah Price
Avg Pettah Price = AVERAGE(fact_historical_prices[retail_price_pettah])

// 3. Average Price Spread (Middleman Margin)
Avg Price Spread = AVERAGE(fact_historical_prices[average_spread])

// 4. Spread Percentage
Spread Percentage = DIVIDE([Avg Price Spread], [Avg Farm Price], 0) * 100

// 5. Total Monthly Rainfall
Total Rainfall = SUM(fact_monthly_weather[rain_sum])

// 6. Mean Temperature
Average Temperature = AVERAGE(fact_monthly_weather[temp_mean])

// 7. Projected Harvest Farm Price (from PyTorch Model)
Projected Harvest Price = AVERAGE(fact_model_forecasts[predicted_farm_price])

// 8. Expected Cultivation Profit Margin %
Expected Profit Margin = AVERAGE(fact_crop_recommendations[profit_margin_pct])
```

---

## 4. Recommended 4-Page Dashboard Layout

### Page 1: Executive Market Overview
- **KPI Cards**: Average Farmgate Price, Average Pettah Retail Price, Average Market Spread %, Number of Monitored Crops.
- **Line Chart**: Historical Price Trends by Crop (Filterable by Date & Crop).
- **Bar Chart**: Retail Spread by Vegetable (Highlights intermediaries' margin).

### Page 2: Agro-Meteorological Impact
- **Dual-Axis Chart**: Monthly Rainfall (Bar) vs. Average Vegetable Price Spike (Line).
- **Scatter Plot**: Temperature Extremes vs. Crop Price Volatility.
- **Slicer**: District and Year selection.

### Page 3: PyTorch Deep Learning Price Forecast
- **Line & Shaded Area Chart**: Historical actual price series transitioning into PyTorch 1-6 month forecast with confidence interval boundaries (`ci_lower`, `ci_upper`).
- **Table View**: Evaluation metrics (MAE, RMSE, MAPE) per crop.

### Page 4: Smart Crop Cultivation Advisor
- **Slicers**: Target Planting Month (e.g. October for Maha season), Farm Location (Badulla / Nuwara Eliya).
- **Ranking Visual**: Top recommended crops ranked by recommendation score.
- **Card Indicators**: Gestation duration, Harvest month, Expected net profit per acre, Weather risk badges.
"""
    with open(guide_path, "w") as f:
        f.write(guide_content)


if __name__ == "__main__":
    generate_powerbi_tables()
