# Power BI Dashboard Setup & Integration Guide

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
