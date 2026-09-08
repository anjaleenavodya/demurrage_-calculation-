# Project Handoff & Execution Manual

## Project Title
**A Weather-Based Vegetable Price and Crop Decision Support Management Information System for Sri Lanka**

---

## Executive Summary
This project delivers a complete, end-to-end Agricultural Management Information System (MIS) designed to support Sri Lankan smallholder farmers, agricultural extension officers, and market analysts. It bridges 25 years of vegetable market price records, 14.5 years of multi-station meteorological records, and primary empirical field surveys collected from smallholder farmers in Badulla and Welimada.

The system combines:
1. **Automated Preprocessing & Relational Database Pipeline**: Cleans raw datasets, aggregates daily weather across 27 monitoring locations to monthly climate variables, engineers cyclical seasonal features, translates all farmer survey records to standardized English with semantic grouping, and populates an SQLite database (`data_processed/agriculture_mis.db`).
2. **PyTorch Deep Learning Sequence Model & Inflation-Aware Forecaster**: Implements a multivariate Stacked Bidirectional LSTM with Temporal Attention and Crop Entity Embeddings using a sliding window approach (6-month historical sequence predicting 1-to-12 months forward or backward farmgate prices with 90% confidence intervals, compounded macroeconomic market inflation, nominal vs constant-rupee pricing, and aligned monthly meteorological condition forecasts).
3. **Sliding-Window Crop Plantation Decision Engine**: Factors in crop gestation cycles (2 to 4 months), predicted harvest prices, estimated production costs, and agro-climatic suitability scores (temperature/rainfall thresholds and flood/drought sensitivity) to recommend the most profitable and climate-resilient crops.
4. **Interactive Streamlit Web Application**: A 5-module dashboard covering executive KPIs, farmer survey analytics, price and weather EDA, PyTorch forward & historical forecast visualizer with market inflation, and interactive crop plantation advisor.
5. **Power BI Integration Package**: Standardized star-schema CSV tables, an executable Power BI Python script connector, and DAX measure specifications.
6. **Unified CLI Orchestrator**: Root entry point (`main.py`) supporting both command-line arguments and an interactive terminal menu.

---

## Mapping to Academic Thesis Chapters

| Thesis Chapter | Documented In Docs | Implemented System Deliverable |
| :--- | :--- | :--- |
| **Chapter 1: Introduction** | Problem Statement & Research Objectives | Aligned 9 vegetable commodities (Beans, Brinjal, Cabbage, Carrot, Green Chilli, Lime, Pumpkin, Snake Gourd, Tomato) addressing price volatility and farmer vulnerability. |
| **Chapter 2: Literature Review** | Comparative analysis of existing apps (Govi Mithuru, GeoGoviya) | Overcomes existing limitations by providing **forward-looking price projections** and **climate-driven crop recommendation**, rather than just reactive historical prices. |
| **Chapter 3: Methodology** | Pragmatism & Design Science Research (DSRM) | Mixed-method empirical execution: secondary data modeling combined with primary survey operationalization from Badulla and Welimada farmers. |
| **Chapter 4: System Requirements** | Operationalization & Functional Requirements | Cleaned and structured farmer survey data (`farmer_survey_cleaned.csv`), SQLite relational database schema, and interactive UX specifications. |
| **Chapter 5: Implementation** | Algorithmic Design & Technology Stack | PyTorch 2.8 BiLSTM neural network (`src/model_pytorch.py`), Sliding Window Recommendation Engine (`src/recommendation_engine.py`), and Streamlit interface (`src/app.py`). |
| **Chapter 6: Testing & Evaluation** | Quantitative & Qualitative Validation | Formal test-set evaluation using Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Mean Absolute Percentage Error (MAPE) on original LKR scale. |

---

## Model Evaluation Metrics (Test Set 2023 - 2024)

| Crop Name | Mean Actual (LKR/kg) | MAE (LKR/kg) | RMSE (LKR/kg) | MAPE (%) | R² Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Beans** | LKR 244.80 | **45.32** | 61.88 | **18.51 %** | -0.605 |
| **Brinjal** | LKR 198.30 | **33.10** | 42.91 | **16.69 %** | -0.349 |
| **Cabbage** | LKR 212.10 | **35.31** | 47.10 | **16.65 %** | -0.430 |
| **Carrot** | LKR 279.20 | **68.01** | 84.22 | **24.36 %** | -2.256 |
| **Green Chilli** | LKR 321.90 | **89.98** | 110.29 | **27.95 %** | -1.828 |
| **Lime** | LKR 386.50 | **123.20** | 143.48 | **31.87 %** | -2.717 |
| **Pumpkin** | LKR 128.60 | **19.14** | 22.20 | **14.88 %** | -0.076 |
| **Snake Gourd** | LKR 135.20 | **25.49** | 30.47 | **18.86 %** | **0.003** |
| **Tomato** | LKR 259.10 | **56.82** | 71.48 | **21.93 %** | -1.331 |
| **OVERALL** | **LKR 240.63** | **LKR 55.15** | **LKR 77.65** | **21.30 %** | **0.121** |

---

## How to Run the Project

All commands should be executed from the project root directory using the virtual environment:

### 1. Launch the Interactive Web Application
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python main.py --app
# Or using Streamlit directly:
/Users/nushan/Projects/Anjalee/Final/.venv/bin/streamlit run src/app.py
```
Open your browser at: **`http://localhost:8501`**

### 2. Re-run Data Preprocessing Pipeline
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python main.py --preprocess
```
This updates all CSVs in `data_processed/` and the SQLite database (`data_processed/agriculture_mis.db`).

### 3. Retrain the PyTorch Model
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python main.py --train --epochs 35
```
This saves the trained weights to `models/pytorch_crop_lstm.pt` and logs metrics to `models/model_metrics.json`.

### 4. Run Model Evaluation
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python main.py --evaluate
```

### 5. Run the Crop Plantation Advisor via CLI
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python main.py --recommend --month 10 --district "Badulla" --acres 1.5
```

### 6. Export Star-Schema Tables for Power BI
```bash
/Users/nushan/Projects/Anjalee/Final/.venv/bin/python main.py --export-powerbi
```

---

## Connecting to Power BI Desktop

### Method 1: Loading Star-Schema CSV Tables (Easiest)
1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Folder** (or **Text/CSV**).
3. Select `/Users/nushan/Projects/Anjalee/Final/exports_powerbi/`.
4. The following tables will be loaded:
   - `fact_historical_prices.csv` (2,772 rows)
   - `fact_monthly_weather.csv` (174 rows)
   - `fact_model_forecasts.csv` (36 rows)
   - `fact_crop_recommendations.csv` (432 rows)
   - `dim_crops.csv` (9 rows)
   - `dim_farmer_survey.csv` (8 rows)

### Method 2: Native Power BI Python Connector
1. In Power BI Desktop: **Get Data** -> **More...** -> **Python script**.
2. Paste the contents of `exports_powerbi/powerbi_live_data_connector.py`.
3. Click **OK** and load all tables.

### Key DAX Measures to Add:
```dax
Avg Farm Price = AVERAGE(fact_historical_prices[farm_price])
Avg Pettah Price = AVERAGE(fact_historical_prices[retail_price_pettah])
Avg Price Spread = AVERAGE(fact_historical_prices[average_spread])
Spread Percentage = DIVIDE([Avg Price Spread], [Avg Farm Price], 0) * 100
Projected Harvest Price = AVERAGE(fact_model_forecasts[predicted_farm_price])
Expected Profit Margin = AVERAGE(fact_crop_recommendations[profit_margin_pct])
```

---

## Deliverables Summary
- **Database**: SQLite Relational DB (`data_processed/agriculture_mis.db`) with indexes.
- **Model**: PyTorch 2.8 BiLSTM sequence forecaster (`models/pytorch_crop_lstm.pt`).
- **Web App**: 6-page interactive Streamlit app (`src/app.py`).
- **Power BI Assets**: 6 Star-Schema tables + Python script + DAX documentation (`exports_powerbi/`).
- **Orchestration**: `main.py` CLI and interactive menu.
- **Documentation**: Updated `Agents.md` and `Handoff.md`.
