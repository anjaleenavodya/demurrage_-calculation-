"""
Crop Plantation Decision & Recommendation Engine
Uses PyTorch time-series price forecasts, historical agro-climatic profiles,
and crop gestation cycles (sliding planting-to-harvest windows) to recommend
the most profitable and climate-resilient crops for Sri Lankan farmers.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.model_pytorch import predict_future_prices
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, "data_processed", "crop_weather_monthly.csv")

# Agronomic Database for Sri Lankan Vegetables (based on Dept of Agriculture benchmarks)
CROP_AGRONOMIC_PROFILES = {
    "Beans": {
        "duration_months": 2,
        "ideal_temp_min": 18.0,
        "ideal_temp_max": 28.0,
        "ideal_rain_min": 80.0,
        "ideal_rain_max": 200.0,
        "flood_sensitivity": "High",
        "drought_tolerance": "Medium",
        "est_cost_per_kg": 150.0,
        "yield_per_acre_kg": 4000,
        "primary_zones": ["Badulla", "Nuwara Eliya", "Matale", "Kandy", "Welimada"],
        "agronomic_tip": "Sensitive to excessive waterlogging. Ensure well-drained loamy soil during monsoon months.",
    },
    "Carrot": {
        "duration_months": 3,
        "ideal_temp_min": 15.0,
        "ideal_temp_max": 24.0,
        "ideal_rain_min": 70.0,
        "ideal_rain_max": 160.0,
        "flood_sensitivity": "Very High",
        "drought_tolerance": "Medium",
        "est_cost_per_kg": 180.0,
        "yield_per_acre_kg": 8000,
        "primary_zones": ["Nuwara Eliya", "Badulla", "Welimada", "Bandarawela"],
        "agronomic_tip": "Thrives in cooler hill-country elevations. High rainfall at root maturation causes cracking.",
    },
    "Cabbage": {
        "duration_months": 3,
        "ideal_temp_min": 16.0,
        "ideal_temp_max": 26.0,
        "ideal_rain_min": 90.0,
        "ideal_rain_max": 220.0,
        "flood_sensitivity": "Medium",
        "drought_tolerance": "Low",
        "est_cost_per_kg": 110.0,
        "yield_per_acre_kg": 10000,
        "primary_zones": ["Nuwara Eliya", "Badulla", "Kandy", "Matale"],
        "agronomic_tip": "High yield potential. Requires uniform soil moisture; apply mulch in dry months.",
    },
    "Tomato": {
        "duration_months": 3,
        "ideal_temp_min": 20.0,
        "ideal_temp_max": 30.0,
        "ideal_rain_min": 60.0,
        "ideal_rain_max": 180.0,
        "flood_sensitivity": "High",
        "drought_tolerance": "Medium",
        "est_cost_per_kg": 140.0,
        "yield_per_acre_kg": 7500,
        "primary_zones": ["Badulla", "Matale", "Kandy", "Anuradhapura", "Jaffna"],
        "agronomic_tip": "Susceptible to fungal blight in heavy continuous rainfall. High market price volatility.",
    },
    "Brinjal": {
        "duration_months": 4,
        "ideal_temp_min": 22.0,
        "ideal_temp_max": 33.0,
        "ideal_rain_min": 60.0,
        "ideal_rain_max": 220.0,
        "flood_sensitivity": "Medium",
        "drought_tolerance": "High",
        "est_cost_per_kg": 120.0,
        "yield_per_acre_kg": 7000,
        "primary_zones": ["Anuradhapura", "Kurunegala", "Matale", "Hambantota", "Badulla"],
        "agronomic_tip": "Hardy warm-season crop. Highly resilient to temperature fluctuations.",
    },
    "Pumpkin": {
        "duration_months": 4,
        "ideal_temp_min": 22.0,
        "ideal_temp_max": 34.0,
        "ideal_rain_min": 50.0,
        "ideal_rain_max": 190.0,
        "flood_sensitivity": "Medium",
        "drought_tolerance": "High",
        "est_cost_per_kg": 70.0,
        "yield_per_acre_kg": 9000,
        "primary_zones": ["Anuradhapura", "Monaragala", "Hambantota", "Polonnaruwa", "Matale"],
        "agronomic_tip": "Low initial input cost and long storage shelf life after harvest.",
    },
    "Green Chilli": {
        "duration_months": 4,
        "ideal_temp_min": 20.0,
        "ideal_temp_max": 32.0,
        "ideal_rain_min": 60.0,
        "ideal_rain_max": 170.0,
        "flood_sensitivity": "Very High",
        "drought_tolerance": "Medium",
        "est_cost_per_kg": 260.0,
        "yield_per_acre_kg": 3500,
        "primary_zones": ["Anuradhapura", "Jaffna", "Puttalam", "Monaragala", "Matale"],
        "agronomic_tip": "High-value commercial crop. Extreme price spikes when supply is hit by unseasonal rain.",
    },
    "Snake Gourd": {
        "duration_months": 3,
        "ideal_temp_min": 22.0,
        "ideal_temp_max": 32.0,
        "ideal_rain_min": 70.0,
        "ideal_rain_max": 210.0,
        "flood_sensitivity": "Medium",
        "drought_tolerance": "Medium",
        "est_cost_per_kg": 95.0,
        "yield_per_acre_kg": 6500,
        "primary_zones": ["Gampaha", "Kalutara", "Kurunegala", "Kandy", "Matale"],
        "agronomic_tip": "Requires trellising or pandal system. Consistent regular harvesting schedule.",
    },
    "Lime": {
        "duration_months": 4,
        "ideal_temp_min": 22.0,
        "ideal_temp_max": 35.0,
        "ideal_rain_min": 50.0,
        "ideal_rain_max": 200.0,
        "flood_sensitivity": "Medium",
        "drought_tolerance": "High",
        "est_cost_per_kg": 200.0,
        "yield_per_acre_kg": 3000,
        "primary_zones": ["Monaragala", "Hambantota", "Anuradhapura", "Polonnaruwa"],
        "agronomic_tip": "Perennial orchard crop. Significant off-season price increases in dry months.",
    },
}


def calculate_weather_suitability(crop_name: str, exp_temp: float, exp_rain: float) -> Tuple[float, List[str]]:
    """
    Computes agro-climatic match score (0.0 - 1.0) and generates risk alerts.
    """
    profile = CROP_AGRONOMIC_PROFILES.get(crop_name)
    if not profile:
        return 0.7, []
        
    score = 1.0
    alerts = []
    
    # Temperature check
    t_min = profile["ideal_temp_min"]
    t_max = profile["ideal_temp_max"]
    if exp_temp < t_min:
        diff = t_min - exp_temp
        score -= min(0.35, diff * 0.08)
        alerts.append(f"Temperature is cooler than optimal ({exp_temp:.1f}°C vs min {t_min}°C). Growth rate may slow.")
    elif exp_temp > t_max:
        diff = exp_temp - t_max
        score -= min(0.35, diff * 0.08)
        alerts.append(f"Heat stress alert ({exp_temp:.1f}°C vs max {t_max}°C). Additional irrigation needed.")
        
    # Rainfall check
    r_min = profile["ideal_rain_min"]
    r_max = profile["ideal_rain_max"]
    if exp_rain < r_min:
        diff = r_min - exp_rain
        score -= min(0.35, (diff / r_min) * 0.3)
        alerts.append(f"Low seasonal precipitation ({exp_rain:.0f}mm vs min {r_min:.0f}mm). High irrigation requirement.")
    elif exp_rain > r_max:
        diff = exp_rain - r_max
        penalty = min(0.45, (diff / r_max) * 0.4)
        if profile["flood_sensitivity"] in ["High", "Very High"]:
            penalty *= 1.2
            alerts.append(f"Excess rainfall / flood risk ({exp_rain:.0f}mm vs max {r_max:.0f}mm). Crop is highly flood-sensitive.")
        else:
            alerts.append(f"Above-average rainfall anticipated ({exp_rain:.0f}mm). Monitor soil drainage.")
        score -= min(0.5, penalty)
        
    return max(0.2, round(score, 2)), alerts


def get_expected_climate_for_month(month: int) -> Tuple[float, float]:
    """
    Retrieves the historical median temperature and rainfall for a specific month in Sri Lanka.
    """
    df = pd.read_csv(PROCESSED_DATA_PATH)
    m_df = df[df["month"] == month]
    if len(m_df) == 0:
        return 26.0, 120.0
    return float(m_df["temp_mean"].median()), float(m_df["rain_sum"].median())


def recommend_crops(
    planting_month: int,
    farm_size_acres: float = 1.0,
    target_district: str = "Badulla",
    risk_preference: str = "Balanced",
) -> List[Dict]:
    """
    Simulates planting-to-harvest sliding window for all crops,
    projects future prices at maturity using PyTorch sequence model,
    evaluates weather suitability, and returns ranked crop recommendations.
    """
    MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    recommendations = []
    
    for crop, profile in CROP_AGRONOMIC_PROFILES.items():
        duration = profile["duration_months"]
        # Harvest month calculation (1-indexed)
        harvest_month = (planting_month + duration - 1) % 12 + 1
        
        # Query PyTorch Model for Price Forecast
        try:
            forecast_data = predict_future_prices(crop)
            # Find closest offset corresponding to crop gestation duration
            offset_idx = min(duration - 1, len(forecast_data["forecasts"]) - 1)
            f_item = forecast_data["forecasts"][offset_idx]
            predicted_farm_price = f_item["predicted_farm_price"]
            ci_lower = f_item["ci_lower"]
            ci_upper = f_item["ci_upper"]
        except Exception:
            # Fallback historical heuristic if model file is unavailable
            df = pd.read_csv(PROCESSED_DATA_PATH)
            c_hist = df[(df["crop_name"] == crop) & (df["month"] == harvest_month)]
            predicted_farm_price = float(c_hist["farm_price"].mean()) if len(c_hist) > 0 else 180.0
            ci_lower = predicted_farm_price * 0.85
            ci_upper = predicted_farm_price * 1.15
            
        # Climate during growing window
        exp_temp, exp_rain = get_expected_climate_for_month(harvest_month)
        suitability_score, weather_alerts = calculate_weather_suitability(crop, exp_temp, exp_rain)
        
        # Economic Analysis
        cost_kg = profile["est_cost_per_kg"]
        yield_kg = profile["yield_per_acre_kg"] * farm_size_acres
        
        # Price used based on risk preference
        if risk_preference == "Conservative / Low Risk":
            effective_price = ci_lower
        elif risk_preference == "Maximum Profit":
            effective_price = ci_upper
        else:
            effective_price = predicted_farm_price
            
        net_profit_per_kg = effective_price - cost_kg
        profit_margin_pct = (net_profit_per_kg / cost_kg) * 100.0
        total_est_cost = cost_kg * yield_kg
        total_est_revenue = effective_price * yield_kg
        total_est_net_profit = total_est_cost * (profit_margin_pct / 100.0)
        
        # District suitability bonus
        district_bonus = 1.1 if target_district in profile["primary_zones"] else 0.95
        
        # Composite Recommendation Score (0 - 100)
        # 45% Profit Margin + 35% Climate Suitability + 20% Downside Safety (ci_lower > cost)
        margin_component = np.clip(profit_margin_pct * 0.6, -20.0, 50.0)
        climate_component = suitability_score * 35.0
        safety_bonus = 15.0 if ci_lower > cost_kg else 0.0
        
        raw_score = (margin_component + climate_component + safety_bonus) * district_bonus
        comp_score = float(np.clip(raw_score, 5.0, 99.0))
        
        # Verdict tier
        if comp_score >= 75:
            verdict = "Highly Recommended"
            verdict_badge = "success"
        elif comp_score >= 60:
            verdict = "Recommended"
            verdict_badge = "primary"
        elif comp_score >= 45:
            verdict = "Moderate / Proceed with Caution"
            verdict_badge = "warning"
        else:
            verdict = "High Risk / Not Advisable"
            verdict_badge = "danger"
            
        recommendations.append({
            "crop_name": crop,
            "rank": 0,
            "recommendation_score": round(comp_score, 1),
            "verdict": verdict,
            "verdict_badge": verdict_badge,
            "planting_month_name": MONTH_NAMES[planting_month - 1],
            "harvest_month_name": MONTH_NAMES[harvest_month - 1],
            "gestation_months": duration,
            "predicted_farm_price_lkr": round(predicted_farm_price, 2),
            "ci_range_lkr": f"{round(ci_lower, 1)} - {round(ci_upper, 1)}",
            "production_cost_per_kg_lkr": cost_kg,
            "net_margin_per_kg_lkr": round(net_profit_per_kg, 2),
            "profit_margin_pct": round(profit_margin_pct, 1),
            "projected_net_profit_total_lkr": round(total_est_net_profit, 0),
            "projected_yield_total_kg": round(yield_kg, 0),
            "climate_suitability_score": round(suitability_score * 100, 1),
            "weather_alerts": weather_alerts,
            "agronomic_tip": profile["agronomic_tip"],
            "primary_zones": profile["primary_zones"],
        })
        
    # Sort descending by recommendation score
    recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
    for idx, item in enumerate(recommendations):
        item["rank"] = idx + 1
        
    return recommendations


if __name__ == "__main__":
    recs = recommend_crops(planting_month=10, farm_size_acres=1.5, target_district="Badulla")
    print("\n Top 3 Recommended Crops for October Planting in Badulla (1.5 Acres):")
    for r in recs[:3]:
        print(f" #{r['rank']} {r['crop_name']} - Score: {r['recommendation_score']}/100 [{r['verdict']}]")
        print(f"    Gestation: {r['gestation_months']}m | Harvest in: {r['harvest_month_name']}")
        print(f"    Expected Farm Price: LKR {r['predicted_farm_price_lkr']} (Range: {r['ci_range_lkr']})")
        print(f"    Estimated Net Profit: LKR {r['projected_net_profit_total_lkr']:,.0f} (Margin: {r['profit_margin_pct']}%)")
        print(f"    Climate Suitability: {r['climate_suitability_score']}%")
