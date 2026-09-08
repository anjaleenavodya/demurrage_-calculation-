# Agents.md: Architecture & Guidelines for Sri Lanka Agri-MIS

## Project Overview
**Title**: A Weather-Based Vegetable Price and Crop Decision Support Management Information System for Sri Lanka  
**Domain**: Agricultural Informatics, Time-Series Sequence Modeling, Decision Support Systems (DSS / MIS)  
**Academic Alignment**: Undergraduate Final Thesis (MIS / CS / SE / DS - UGC), following Pragmatism paradigm and Design Science Research Methodology (DSRM).

---

## System Architecture

```
                                  DATA SOURCES
   ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
   │ sri_lanka_crop_prices   │  │       weatherData       │  │    Untitled form.csv    │
   │ (Kaggle / HARTI)        │  │ (Dept. of Meteorology)  │  │ (Farmer Survey - Badulla│
   │ 9 Crops (2000-2025)     │  │ 27 Stations (2010-2024) │  │  & Welimada smallholders)│
   └────────────┬────────────┘  └────────────┬────────────┘  └────────────┬────────────┘
                │                            │                            │
                ▼                            ▼                            ▼
   ┌───────────────────────────────────────────────────────────────────────────────────┐
   │                         SRC/DATA_PREPROCESSING.PY                                 │
   │ - Daily to monthly meteorological aggregation across 27 monitoring stations       │
   │ - Price normalization, cyclical month encodings, and spread computations          │
   │ - Multi-variate lag feature alignment (1,566 monthly crop-weather records)        │
   │ - SQLite Database population (data_processed/agriculture_mis.db)                  │
   └─────────────────────────────────────────┬─────────────────────────────────────────┘
                                             │
                                             ▼
   ┌───────────────────────────────────────────────────────────────────────────────────┐
   │                           SRC/MODEL_PYTORCH.PY                                    │
   │ - PyTorch Sliding Window Dataset (6-month sequence -> 4-month forecast horizon)   │
   │ - Deep Bi-directional LSTM with Crop Entity Embeddings & Temporal Attention       │
   │ - Multi-horizon farmgate price forecasting with 90% confidence interval bounds    │
   │ - Evaluation across 9 crops: MAE (LKR/kg), RMSE, MAPE (%), R² score               │
   └────────────────────┬────────────────────────────────────────────┬─────────────────┘
                        │                                            │
                        ▼                                            ▼
   ┌───────────────────────────────────────────┐  ┌────────────────────────────────────┐
   │        SRC/RECOMMENDATION_ENGINE.PY       │  │        SRC/POWERBI_EXPORT.PY       │
   │ - Agronomic gestation database (2-4 mos)  │  │ - Star-Schema Fact & Dim CSVs      │
   │ - Agro-climatic suitability scoring       │  │ - Power BI Python script connector │
   │ - Sliding-window harvest price projection │  │ - DAX measures & dashboard layout  │
   │ - Net profit margin & crop ranking engine │  │   specifications                   │
   └────────────────────┬──────────────────────┘  └──────────────────┬─────────────────┘
                        │                                            │
                        ▼                                            ▼
   ┌───────────────────────────────────────────────────────────────────────────────────┐
   │                                   USER SURFACES                                   │
   │  1. Streamlit Web App (src/app.py): Interactive farmer & researcher dashboard     │
   │  2. Unified CLI (main.py): Pipeline execution, training, evaluation, & advisor    │
   └───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure
```
/Users/nushan/Projects/Anjalee/Final/
├── .streamlit/
│   └── config.toml                  # Streamlit configuration (headless, theme)
├── .venv/                           # Python 3.9 virtual environment
├── Dataset/
│   ├── sri_lanka_crop_prices.csv    # 2,772 monthly price records (9 crops)
│   ├── weatherData.csv              # 142,371 daily records (27 locations)
│   └── Untitled form.csv            # Primary field survey (Badulla/Welimada)
├── Docs/
│   ├── Detailed and Elaboratory Thesis chapter breakdown3.pdf
│   ├── Detailed and Elaboratory Thesis chapter breakdown v1.1 (4) (2).docx
│   └── Thesis chapter breakdown (3).docx
├── data_processed/                  # Preprocessed clean datasets & SQLite database
│   ├── agriculture_mis.db           # Relational SQLite database
│   ├── crop_prices_clean.csv        # Cleaned price series
│   ├── crop_weather_monthly.csv     # Aligned multivariate time-series
│   ├── farmer_survey_cleaned.csv    # Translated & structured survey responses
│   ├── weather_monthly_by_location.csv
│   └── weather_monthly_national.csv
├── exports_powerbi/                 # Ready-to-import Star Schema tables for Power BI
│   ├── fact_historical_prices.csv
│   ├── fact_monthly_weather.csv
│   ├── fact_model_forecasts.csv
│   ├── fact_crop_recommendations.csv
│   ├── dim_crops.csv
│   ├── dim_farmer_survey.csv
│   ├── powerbi_live_data_connector.py
│   └── POWERBI_SETUP_GUIDE.md
├── models/                          # Saved model weights & evaluation artifacts
│   ├── pytorch_crop_lstm.pt         # PyTorch BiLSTM model checkpoint
│   ├── feature_scaler.joblib        # Scikit-learn StandardScaler
│   └── model_metrics.json           # Evaluation metrics per crop
├── src/
│   ├── __init__.py
│   ├── data_preprocessing.py        # Cleaning, aggregation, and DB loading
│   ├── model_pytorch.py             # PyTorch LSTM architecture, training, and inference
│   ├── recommendation_engine.py     # Crop gestation and agro-climatic ranking logic
│   ├── powerbi_export.py            # Power BI star-schema exporter
│   └── app.py                       # Streamlit multi-tab web application
├── main.py                          # Unified CLI entry point
├── Guide.md                         # Simplified step-by-step execution guide
├── Agents.md                        # AI agent & developer guidelines (this file)
└── Handoff.md                       # Project handover & execution manual
```

---

## Core Data Schema

### 1. Crop Prices Fact (`crop_prices_clean.csv`)
- `crop_name`: Vegetable commodity name (Beans, Brinjal, Cabbage, Carrot, Green Chilli, Lime, Pumpkin, Snake Gourd, Tomato).
- `date`: Month start date (`YYYY-MM-DD`).
- `farm_price`: Producer / farmgate price in Sri Lankan Rupees per kilogram (LKR/kg).
- `retail_price_pettah`: Wholesale/retail price in Colombo Central Market (Pettah).
- `retail_price_dambulla`: Dedicated Economic Centre price (Dambulla).
- `average_spread`: Price differential between farmgate and retail.
- `spread_pct`: Percentage margin captured by intermediaries.

### 2. Meteorological Data (`weather_monthly_national.csv`)
- `temp_mean`, `temp_max`, `temp_min`: Monthly average, extreme maximum, and minimum ambient temperatures (°C).
- `rain_sum`: Monthly cumulative rainfall (mm).
- `rain_days`: Count of days with rainfall $\ge 1.0\text{ mm}$.
- `sunshine_mean_hours`: Daily average hours of bright sunshine.
- `radiation_mean`: Solar shortwave radiation ($MJ/m^2$).
- `et0_mean`: FAO reference evapotranspiration (mm).

### 3. PyTorch Model Input Tensor (`CropTimeSeriesDataset`)
- Sequence length $L = 6$ consecutive months.
- Input feature dimension $D = 15$ continuous variables + 8-dimensional crop entity embedding.
- Multi-horizon forward and backward fluctuation simulator: `predict_price_and_weather_fluctuations(crop, start_year, start_month, horizon, direction, annual_inflation_rate, district)` generates month-over-month price changes ($\Delta P$, $\% \Delta P$) compounded with macroeconomic market inflation, comparing nominal vs constant-rupee prices alongside forward meteorological forecasts (temperature, rainfall, rain days, climate risk level).


### 4. Smallholder Farmer Survey Schema (`farmer_survey` in SQLite & `dim_farmer_survey.csv`)
All raw Sinhala responses are translated to standardized English and semantically clustered:
- `farmer_name`: Standardized English names (e.g. Madhawa Sandaruwan, Maleesha, Nuwan Chathuranga).
- `district` & `sub_region`: Semantically clustered regions (`Badulla Central`, `Welimada Division`).
- `age_group`: Standardized brackets (`Under 30`, `30 - 45`).
- `gender`: English normalized (`Male`, `Female`).
- `experience_years` & `experience_tier`: Numerical years and grouped tiers (`1 - 5 Years (Early Career)`, `6 - 10 Years (Experienced)`, `15+ Years (Veteran Farmer)`).
- `farm_size_acres` & `farm_size_category`: Grouped categories (`Smallholder (0.5 - 1.0 Ac)`, `Medium Smallholder (1.0 - 2.0 Ac)`, `Commercial Smallholder (> 2.0 Ac)`).
- `main_crops`: Translated comma-separated commodities (`Carrot`, `Beans`, `Leeks`).
- `price_volatility_impact`: Normalized impact levels (`High / Frequent Loss`, `Moderate / Occasional Loss`).
- `causes_of_volatility`: Grouped core drivers (`Adverse Weather (Monsoon / Drought)`, `Intermediary / Middleman Margins`, `Market Glut / Overproduction`).
- `other_causes_elaborated`: Full English translations of regional farming zoning issues and distribution bottlenecks.
- `info_source`: Standardized channels (`Mobile Agricultural Apps`, `Mass Media`, `Peer Farmers & Social Networks`, `Direct Visits to Wholesale Boutiques`).
- `demand_price_forecast` & `demand_crop_recommendation`: Unanimous `Yes`.
- `preferred_platform`: English devices (`Mobile Smartphone`, `Both Mobile & Desktop Web`).
- `wanted_features`: Grouped features (`Forward Price Forecasting`, `Agro-Climatic Crop Cultivation Recommendations`).
- `feedback_notes`: Full English translations of farmer recommendations.

---

## Command Reference

| Action | Terminal Command |
| :--- | :--- |
| **Run Full Pipeline** | `python main.py --all` |
| **Data Preprocessing** | `python main.py --preprocess` |
| **Train PyTorch Model** | `python main.py --train --epochs 35` |
| **Evaluate Model** | `python main.py --evaluate` |
| **Run Crop Advisor** | `python main.py --recommend --month 10 --district Badulla` |
| **Export for Power BI** | `python main.py --export-powerbi` |
| **Launch Streamlit App**| `python main.py --app` (or `streamlit run src/app.py`) |
| **Interactive Menu** | `python main.py` |

---

## Guidelines for Future AI Agents & Developers
1. **Always use the virtual environment**: Ensure all scripts use `/Users/nushan/Projects/Anjalee/Final/.venv/bin/python`.
2. **Preserve model cache**: `src/model_pytorch.py` uses `get_cached_model()` for fast in-memory inference. Do not remove in-memory caching to avoid redundant disk I/O during multi-crop simulations.
3. **Database consistency**: Whenever raw datasets are modified, run `python main.py --preprocess` followed by `python main.py --export-powerbi` to keep the SQLite database and Power BI exports synchronized.
4. **Reproducibility**: When retraining PyTorch models, maintain train/test chronological split (`train < 2023`, `test >= 2023`) to prevent lookahead data leakage in time-series validation.
