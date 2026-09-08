# ==============================================================================
# Power BI Desktop Python Script Data Connector
# Usage:
#   1. In Power BI Desktop, click "Get Data" -> "More..." -> "Python script"
#   2. Copy and paste this script into the prompt and click OK.
# ==============================================================================

import pandas as pd
import os

EXPORTS_DIR = r"/Users/nushan/Projects/Anjalee/Final/exports_powerbi"

# Load Star-Schema tables into Power BI Data Model
fact_prices = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_historical_prices.csv"))
fact_weather = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_monthly_weather.csv"))
fact_forecasts = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_model_forecasts.csv"))
fact_crop_recommendations = pd.read_csv(os.path.join(EXPORTS_DIR, "fact_crop_recommendations.csv"))
dim_crops = pd.read_csv(os.path.join(EXPORTS_DIR, "dim_crops.csv"))
dim_farmer_survey = pd.read_csv(os.path.join(EXPORTS_DIR, "dim_farmer_survey.csv"))
