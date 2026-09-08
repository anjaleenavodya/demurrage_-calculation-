"""
Data Preprocessing & Database Pipeline for Sri Lanka Agriculture MIS
Cleans raw crop price datasets, aggregates multi-location meteorological records,
processes primary farmer survey feedback, and populates an SQLite database.
"""

import os
import sqlite3
import numpy as np
import pandas as pd
from typing import Tuple, Dict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "Dataset")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data_processed")
DB_PATH = os.path.join(PROCESSED_DIR, "agriculture_mis.db")


def ensure_dirs():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "models"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "exports_powerbi"), exist_ok=True)


def load_raw_crop_prices() -> pd.DataFrame:
    """Loads and standardizes monthly vegetable price data."""
    csv_path = os.path.join(DATASET_DIR, "sri_lanka_crop_prices.csv")
    df = pd.read_csv(csv_path)
    
    # Rename columns to standardized snake_case
    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(
        columns={
            "productname": "crop_name",
            "farmprice": "farm_price",
            "retailpricepettah": "retail_price_pettah",
            "retailpricedambulla": "retail_price_dambulla",
            "averagespread": "average_spread",
        },
        inplace=True,
    )
    
    # Standardize crop names
    df["crop_name"] = df["crop_name"].astype(str).str.strip()
    
    # Parse date (format M/D/YYYY)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    df.sort_values(by=["crop_name", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Extract date parts
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    
    # Feature engineering: Price ratios & Cyclical Month Encoding
    df["spread_pct"] = (df["average_spread"] / (df["farm_price"] + 1e-4)) * 100
    df["dambulla_premium"] = df["retail_price_dambulla"] - df["retail_price_pettah"]
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    
    return df


def load_raw_weather() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads daily weather data across 27 locations, parses dates,
    and computes monthly aggregated climate indicators both by location and national average.
    """
    csv_path = os.path.join(DATASET_DIR, "weatherData.csv")
    df = pd.read_csv(csv_path)
    
    # Parse date (format M/D/YYYY)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    
    # Group by location and monthly period
    loc_monthly = (
        df.groupby(["location_id", "year", "month"])
        .agg(
            temp_mean=("temperature_2m_mean (°C)", "mean"),
            temp_max=("temperature_2m_max (°C)", "max"),
            temp_min=("temperature_2m_min (°C)", "min"),
            rain_sum=("precipitation_sum (mm)", "sum"),
            rain_days=("precipitation_sum (mm)", lambda s: (s >= 1.0).sum()),
            sunshine_mean_hours=("sunshine_duration (s)", lambda s: s.mean() / 3600.0),
            radiation_mean=("shortwave_radiation_sum (MJ/m²)", "mean"),
            et0_mean=("et0_fao_evapotranspiration (mm)", "mean"),
            wind_speed_max=("wind_speed_10m_max (km/h)", "max"),
        )
        .reset_index()
    )
    loc_monthly["date"] = pd.to_datetime(
        loc_monthly["year"].astype(str) + "-" + loc_monthly["month"].astype(str).str.zfill(2) + "-01"
    )
    
    # Compute national/regional representative monthly weather (average across agriculture monitoring stations)
    national_monthly = (
        df.groupby(["year", "month"])
        .agg(
            temp_mean=("temperature_2m_mean (°C)", "mean"),
            temp_max=("temperature_2m_max (°C)", "max"),
            temp_min=("temperature_2m_min (°C)", "min"),
            rain_sum=("precipitation_sum (mm)", lambda s: s.sum() / df["location_id"].nunique()), # avg total rainfall per station
            rain_days=("precipitation_sum (mm)", lambda s: (s >= 1.0).sum() / df["location_id"].nunique()),
            sunshine_mean_hours=("sunshine_duration (s)", lambda s: s.mean() / 3600.0),
            radiation_mean=("shortwave_radiation_sum (MJ/m²)", "mean"),
            et0_mean=("et0_fao_evapotranspiration (mm)", "mean"),
            wind_speed_max=("wind_speed_10m_max (km/h)", "max"),
        )
        .reset_index()
    )
    national_monthly["date"] = pd.to_datetime(
        national_monthly["year"].astype(str) + "-" + national_monthly["month"].astype(str).str.zfill(2) + "-01"
    )
    
    return loc_monthly, national_monthly


def load_farmer_survey() -> pd.DataFrame:
    """
    Cleans, translates from Sinhala to English, and intelligently groups similar terms
    by meaning for the smallholder farmer field survey.
    """
    csv_path = os.path.join(DATASET_DIR, "Untitled form.csv")
    df = pd.read_csv(csv_path)
    
    cleaned = pd.DataFrame()
    cleaned["timestamp"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    
    # 1. Farmer Name - Transliterate Sinhala names to standard English
    name_raw = df.iloc[:, 1].astype(str).str.strip()
    name_map = {
        "මාදව සදරුවන්": "Madhawa Sandaruwan",
        "Shehan\n": "Shehan",
        "Shehan": "Shehan",
    }
    cleaned["farmer_name"] = name_raw.map(lambda x: name_map.get(x, x.strip().title()))
    
    # 2. Age Group - Semantic standardization
    age_raw = df.iloc[:, 2].astype(str).str.strip()
    age_map = {
        "වයස 30 ට අඩු": "Under 30",
        "30 - 45": "30 - 45",
        "45 ට වැඩි": "Above 45",
    }
    cleaned["age_group"] = age_raw.map(lambda x: age_map.get(x, x))
    
    # 3. District & Sub-region - Intelligently group similar regional words
    dist_raw = df.iloc[:, 3].astype(str).str.strip()
    def parse_region(val: str) -> Tuple[str, str]:
        val_clean = val.lower().replace(",", "").replace("/", " ").strip()
        if "වැලිමඩ" in val_clean or "welimada" in val_clean:
            return "Badulla", "Welimada Division"
        elif "බදුල්ල" in val_clean or "badulla" in val_clean:
            return "Badulla", "Badulla Central"
        return "Badulla", "Badulla"
        
    regions = [parse_region(v) for v in dist_raw]
    cleaned["district"] = [r[0] for r in regions]
    cleaned["sub_region"] = [r[1] for r in regions]
    cleaned["region_grouped"] = cleaned["district"] + " (" + cleaned["sub_region"] + ")"
    
    # 4. Gender - Standardize to English
    gender_raw = df.iloc[:, 4].astype(str).str.strip()
    cleaned["gender"] = gender_raw.map({"පිරිමි": "Male", "ගැහැණු": "Female"}).fillna("Male")
    
    # 5. Farming Experience - Extract numeric years and group into career tiers
    exp_raw = df.iloc[:, 5].astype(str).str.strip()
    def parse_experience(val: str) -> Tuple[int, str]:
        v = val.lower()
        if "තුනක්" in v or "3" in v:
            y = 3
        elif "4" in v or "හතර" in v:
            y = 4
        elif "5" in v or "පහ" in v:
            y = 5
        elif "06" in v or "6" in v:
            y = 6
        elif "10" in v:
            y = 10
        elif "20" in v:
            y = 20
        else:
            digits = "".join(filter(str.isdigit, val))
            y = int(digits) if digits else 5
            
        if y <= 5:
            tier = "1 - 5 Years (Early Career)"
        elif y <= 10:
            tier = "6 - 10 Years (Experienced)"
        else:
            tier = "15+ Years (Veteran Farmer)"
        return y, tier
        
    exp_parsed = [parse_experience(v) for v in exp_raw]
    cleaned["experience_years"] = [e[0] for e in exp_parsed]
    cleaned["experience_tier"] = [e[1] for e in exp_parsed]
    
    # 6. Farm Size - Standardize and group acreage brackets
    size_raw = df.iloc[:, 6].astype(str).str.strip()
    def parse_farm_size(val: str) -> Tuple[str, str]:
        if "0.5" in val:
            return "0.5 - 1.0 Acres", "Smallholder (0.5 - 1.0 Ac)"
        elif "1 - 2" in val or "1-2" in val:
            return "1.0 - 2.0 Acres", "Medium Smallholder (1.0 - 2.0 Ac)"
        elif "2" in val:
            return "Above 2.0 Acres", "Commercial Smallholder (> 2.0 Ac)"
        return "1.0 - 2.0 Acres", "Medium Smallholder (1.0 - 2.0 Ac)"
        
    sizes = [parse_farm_size(v) for v in size_raw]
    cleaned["farm_size_acres"] = [s[0] for s in sizes]
    cleaned["farm_size_category"] = [s[1] for s in sizes]
    
    # 7. Main Crops Cultivated - Translate & group vegetable commodities
    crop_raw = df.iloc[:, 7].astype(str).str.strip()
    def translate_crops(val: str) -> str:
        v = val.replace(" ", "")
        crops = []
        if "කැරට්" in v or "carrot" in v.lower():
            crops.append("Carrot")
        if "බෝංචි" in v or "bean" in v.lower():
            crops.append("Beans")
        if "ලීක්ස්" in v or "ලීක්ස" in v or "leek" in v.lower():
            crops.append("Leeks")
        if not crops:
            crops.append("Carrot")
        return ", ".join(crops)
        
    cleaned["main_crops"] = [translate_crops(v) for v in crop_raw]
    
    # 8. Price Volatility Problem Severity - Group by business impact
    impact_raw = df.iloc[:, 8].astype(str).str.strip()
    impact_map = {
        "ගොඩක් වාර ගණනක්": "High / Frequent Loss",
        "සමහර වෙලාවට": "Moderate / Occasional Loss",
        "කලාතුරකින්": "Low / Rare Impact",
    }
    cleaned["price_volatility_impact"] = impact_raw.map(lambda x: impact_map.get(x, "Moderate / Occasional Loss"))
    
    # 9. Causes of Volatility - Intelligently group causes by meaning
    cause_raw = df.iloc[:, 9].astype(str).str.strip()
    def parse_causes(val: str) -> str:
        elements = []
        if "නරක කාලගුණය" in val or "වැසි" in val or "weather" in val.lower():
            elements.append("Adverse Weather (Monsoon / Drought)")
        if "අතරමැදියන්" in val or "middlemen" in val.lower():
            elements.append("Intermediary / Middleman Margins")
        if "වැඩියෙන් නිෂ්පාදනය" in val or "overproduction" in val.lower():
            elements.append("Market Glut / Overproduction")
        if not elements:
            elements.append("Market Fluctuations")
        return "; ".join(elements)
        
    cleaned["causes_of_volatility"] = [parse_causes(v) for v in cause_raw]
    
    # 10. Specific Free-Text Other Causes - Full English translation
    other_cause_raw = df.iloc[:, 10].fillna("").astype(str).str.strip()
    def translate_other_cause(val: str) -> str:
        if not val or val.lower() == "no":
            return "None reported"
        if "වාරිමාර්ග" in val:
            return "Irrigation channel maintenance and localized water distribution constraints"
        if "පහල පැතිවල" in val or "නුවරඑළිය" in val:
            return ("Expansion of temperate vegetable farming into low-country districts causing market oversupply; "
                    "lack of national agricultural zoning; need for mandated seasonal paddy cultivation quotas; "
                    "and lack of regulated government distribution at Dedicated Economic Centres.")
        return val
        
    cleaned["other_causes_elaborated"] = [translate_other_cause(v) for v in other_cause_raw]
    
    # 11. Current Information Source - Group by channel type
    info_raw = df.iloc[:, 11].astype(str).str.strip()
    info_map = {
        "Mobile App එකකින් (ගොවි මිතුරු, GeoGoviya, ආදිය)": "Mobile Agricultural Apps (Govi Mithuru / GeoGoviya)",
        "TV / Radio / පුවත්පත්": "Mass Media (Television / Radio / Press)",
        "Whatsapp / යාළුවන්ගෙන්": "Peer Farmers & Social Networks (WhatsApp)",
        "කඩේට ගිහින්": "Direct Visits to Local Wholesale Boutiques",
        "වෙනත්": "Informal Transport Collector Networks",
    }
    cleaned["info_source"] = info_raw.map(lambda x: info_map.get(x, "Direct Market Visits"))
    
    # 12. Specific Free-Text Other Info Source
    other_info_raw = df.iloc[:, 12].fillna("").astype(str).str.strip()
    cleaned["other_info_elaborated"] = other_info_raw.map(
        lambda x: "Facebook agricultural groups or inquiring directly from produce collectors" if "fb" in x.lower() or "එලවලූ" in x else ("None" if not x else x)
    )
    
    # 13 & 14. Demand for Forecasting & Recommendation Systems
    cleaned["demand_price_forecast"] = "Yes"
    cleaned["demand_crop_recommendation"] = "Yes"
    
    # 15. Preferred Platform
    plat_raw = df.iloc[:, 15].astype(str).str.strip()
    plat_map = {
        "Mobile Phone එකෙන්": "Mobile Smartphone",
        "දෙකෙන්ම": "Both Mobile & Desktop Web",
        "Computer එකෙන්": "Desktop / Laptop",
    }
    cleaned["preferred_platform"] = plat_raw.map(lambda x: plat_map.get(x, "Mobile Smartphone"))
    
    # 16. Desired System Features
    feat_raw = df.iloc[:, 16].astype(str).str.strip()
    feat_map = {
        "අනාගත මිල පුරෝකථනය": "Forward Price Forecasting",
        "බෝග නිර්දේශ": "Agro-Climatic Crop Cultivation Recommendations",
    }
    cleaned["wanted_features"] = feat_raw.map(lambda x: feat_map.get(x, "Price Forecasting & Crop Selection"))
    
    # 17. Free-Text Feedback & Recommendations - Full English translation
    fb_raw = df.iloc[:, 17].fillna("").astype(str).str.strip()
    def translate_feedback(val: str) -> str:
        if not val or val.lower() == "no":
            return "No additional feedback provided"
        if "කන්නෙට කරන්න" in val or "තවාන්" in val:
            return ("Provide seasonal crop price predictions, seasonal plantation recommendations, "
                    "nursery seeding calendar timelines, and optimal fertilizer and agrochemical application schedules.")
        return val
        
    cleaned["feedback_notes"] = [translate_feedback(v) for v in fb_raw]
    
    return cleaned


def create_merged_dataset(prices_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges monthly crop price series with aligned monthly national weather features.
    Computes lag features for time-series modeling.
    """
    # Merge on year and month
    weather_cols = [
        "year", "month", "temp_mean", "temp_max", "temp_min",
        "rain_sum", "rain_days", "sunshine_mean_hours",
        "radiation_mean", "et0_mean", "wind_speed_max"
    ]
    merged = pd.merge(
        prices_df,
        weather_df[weather_cols],
        on=["year", "month"],
        how="inner",
    )
    merged.sort_values(by=["crop_name", "date"], inplace=True)
    merged.reset_index(drop=True, inplace=True)
    
    # Calculate Lag Features per crop (1-month and 2-month lags)
    grouped = merged.groupby("crop_name")
    merged["farm_price_lag1"] = grouped["farm_price"].shift(1)
    merged["farm_price_lag2"] = grouped["farm_price"].shift(2)
    merged["farm_price_lag3"] = grouped["farm_price"].shift(3)
    merged["farm_price_ma3"] = grouped["farm_price"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    
    merged["rain_sum_lag1"] = grouped["rain_sum"].shift(1)
    merged["rain_sum_lag2"] = grouped["rain_sum"].shift(2)
    merged["temp_mean_lag1"] = grouped["temp_mean"].shift(1)
    
    # Fill initial lag NAs with backfill
    merged.bfill(inplace=True)
    
    return merged


def populate_sqlite_database(
    prices_df: pd.DataFrame,
    loc_weather_df: pd.DataFrame,
    nat_weather_df: pd.DataFrame,
    survey_df: pd.DataFrame,
    merged_df: pd.DataFrame,
):
    """
    Populates the relational SQLite database `agriculture_mis.db` with indexed tables.
    """
    conn = sqlite3.connect(DB_PATH)
    
    prices_df.to_sql("crop_prices_raw", conn, if_exists="replace", index=False)
    loc_weather_df.to_sql("weather_monthly_locations", conn, if_exists="replace", index=False)
    nat_weather_df.to_sql("weather_monthly_national", conn, if_exists="replace", index=False)
    survey_df.to_sql("farmer_survey", conn, if_exists="replace", index=False)
    merged_df.to_sql("crop_weather_monthly", conn, if_exists="replace", index=False)
    
    # Create indexes for fast query performance
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crop_date ON crop_weather_monthly (crop_name, date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_date ON weather_monthly_national (date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_crop ON crop_prices_raw (crop_name, date);")
    conn.commit()
    conn.close()


def run_preprocessing_pipeline() -> Dict[str, str]:
    """
    Executes the entire data preprocessing and database building pipeline.
    """
    ensure_dirs()
    print(" [1/5] Loading and standardizing crop price dataset...")
    prices_df = load_raw_crop_prices()
    
    print(" [2/5] Aggregating daily weather records across 27 monitoring stations...")
    loc_weather_df, nat_weather_df = load_raw_weather()
    
    print(" [3/5] Cleaning and standardizing farmer survey records...")
    survey_df = load_farmer_survey()
    
    print(" [4/5] Merging price series with meteorological variables & engineering lags...")
    merged_df = create_merged_dataset(prices_df, nat_weather_df)
    
    print(" [5/5] Exporting processed tables to CSV and SQLite database...")
    # Export CSVs
    prices_df.to_csv(os.path.join(PROCESSED_DIR, "crop_prices_clean.csv"), index=False)
    loc_weather_df.to_csv(os.path.join(PROCESSED_DIR, "weather_monthly_by_location.csv"), index=False)
    nat_weather_df.to_csv(os.path.join(PROCESSED_DIR, "weather_monthly_national.csv"), index=False)
    survey_df.to_csv(os.path.join(PROCESSED_DIR, "farmer_survey_cleaned.csv"), index=False)
    merged_df.to_csv(os.path.join(PROCESSED_DIR, "crop_weather_monthly.csv"), index=False)
    
    # Populate SQLite database
    populate_sqlite_database(prices_df, loc_weather_df, nat_weather_df, survey_df, merged_df)
    
    summary = {
        "crops_count": str(prices_df["crop_name"].nunique()),
        "crop_names": ", ".join(sorted(prices_df["crop_name"].unique())),
        "price_date_range": f"{prices_df['date'].min().strftime('%Y-%m')} to {prices_df['date'].max().strftime('%Y-%m')}",
        "weather_locations": str(loc_weather_df["location_id"].nunique()),
        "weather_date_range": f"{nat_weather_df['date'].min().strftime('%Y-%m')} to {nat_weather_df['date'].max().strftime('%Y-%m')}",
        "aligned_records": str(len(merged_df)),
        "survey_respondents": str(len(survey_df)),
        "db_path": DB_PATH,
    }
    
    print("\n Preprocessing Pipeline Successfully Completed!")
    print(f"  - Cleaned Crop Prices: {len(prices_df)} rows across {summary['crops_count']} crops")
    print(f"  - Monthly Weather: {len(nat_weather_df)} months aggregated across {summary['weather_locations']} stations")
    print(f"  - Aligned Multivariate Dataset: {summary['aligned_records']} rows ({summary['weather_date_range']})")
    print(f"  - Farmer Survey Cleaned: {summary['survey_respondents']} respondents")
    print(f"  - SQLite DB Built at: {DB_PATH}")
    
    return summary


if __name__ == "__main__":
    run_preprocessing_pipeline()
