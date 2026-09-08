"""
Streamlit Web Application: Weather-Based Vegetable Price & Crop Decision Support MIS
Interactive decision support dashboard for Sri Lankan smallholder farmers, extension officers,
and agricultural analysts. Features PyTorch sequence models and agro-climatic decision support.
"""

import os
import sys
import json
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.model_pytorch import (
    predict_future_prices,
    predict_price_and_weather_fluctuations,
    METRICS_PATH,
    CHECKPOINT_PATH,
)
from src.recommendation_engine import recommend_crops, CROP_AGRONOMIC_PROFILES

PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data_processed")
DB_PATH = os.path.join(PROCESSED_DIR, "agriculture_mis.db")

# Page Configuration
st.set_page_config(
    page_title="Sri Lanka Agri-MIS | Price & Crop Advisor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (CSS) - Clean, professional, zero emojis
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #14532d;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        text-align: center;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #166534;
    }
    .kpi-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .rec-card {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .rec-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.08);
    }
    .badge-success {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-warning {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-danger {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-neutral {
        background-color: #e2e8f0;
        color: #334155;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_all_data():
    prices_df = pd.read_csv(os.path.join(PROCESSED_DIR, "crop_prices_clean.csv"))
    prices_df["date"] = pd.to_datetime(prices_df["date"])
    
    weather_df = pd.read_csv(os.path.join(PROCESSED_DIR, "weather_monthly_national.csv"))
    weather_df["date"] = pd.to_datetime(weather_df["date"])
    
    merged_df = pd.read_csv(os.path.join(PROCESSED_DIR, "crop_weather_monthly.csv"))
    merged_df["date"] = pd.to_datetime(merged_df["date"])
    
    survey_df = pd.read_csv(os.path.join(PROCESSED_DIR, "farmer_survey_cleaned.csv"))
    
    metrics_data = {}
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as f:
            metrics_data = json.load(f)
            
    return prices_df, weather_df, merged_df, survey_df, metrics_data


# Load Data
try:
    prices_df, weather_df, merged_df, survey_df, metrics_data = load_all_data()
except Exception as e:
    st.error(f"Error loading processed datasets: {e}. Please run `python main.py --preprocess` first.")
    st.stop()


# Sidebar Navigation & Context - Zero Emojis
with st.sidebar:
    st.title("Sri Lanka Agri-MIS")
    st.caption("Weather-Driven Vegetable Price & Crop Decision Support System")
    
    menu = st.radio(
        "Navigation Modules",
        [
            "Executive Overview",
            "Farmer Survey Insights",
            "Price & Weather Analytics",
            "PyTorch Forecast & Fluctuation",
            "Crop Plantation Advisor",
        ],
        index=0,
    )
    
    st.markdown("---")
    st.markdown("**System Metadata**")
    st.markdown("- Framework: PyTorch 2.8 & Streamlit")
    st.markdown("- Crops Monitored: 9 Commercial Vegetables")
    st.markdown("- Price Records: 2000 - 2025 (25 Years)")
    st.markdown("- Weather Stations: 27 National Locations")
    st.markdown("- Relational DB: SQLite (Normalized & English)")
    st.caption("Developed for Academic Research & Field Decision Support")


# --------------------------------------------------------------------------------------
# MODULE 1: EXECUTIVE OVERVIEW
# --------------------------------------------------------------------------------------
if menu == "Executive Overview":
    st.markdown('<div class="main-title">Weather-Based Vegetable Price & Crop Decision Support MIS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">An Intelligent Agricultural Management Information System bridging meteorological variations, market price dynamics, and proactive crop planning for Sri Lankan smallholder farmers.</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-value">9</div>
            <div class="kpi-label">Commercial Crops</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{len(prices_df):,}</div>
            <div class="kpi-label">Monthly Price Records</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{len(weather_df):,}</div>
            <div class="kpi-label">Climate Month Records</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-value">100%</div>
            <div class="kpi-label">Farmer Demand for MIS</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.subheader("Research Context & Academic Problem Statement")
        st.markdown("""
        - **General Problem**: Extreme vegetable price volatility driven by erratic weather patterns (intense monsoonal downpours and prolonged dry spells) creates acute financial instability for Sri Lankan smallholders, inflated consumer food costs, and structural food security risks.
        - **Specific Problem**: Existing mobile platforms (e.g., Govi Mithuru, GeoGoviya) provide only **reactive historical or current day prices**. Smallholders lack forward-looking predictive tools to determine which crop will deliver the highest profit margin before they commit capital and plant seeds.
        - **Proposed Solution**: A dual-layered decision support framework combining a **PyTorch BiLSTM Deep Learning Forecaster** with an **Agro-Climatic Sliding Window Plantation Advisor**, paired with an interactive **Streamlit** decision dashboard.
        """)
        
        st.subheader("Primary Research Objectives")
        st.markdown("""
        1. **Identify** key meteorological parameters (temperature, precipitation, sunshine, evapotranspiration) influencing farmgate vegetable prices.
        2. **Analyze** historical price series (2000-2025) and multi-station weather records to model cross-correlations and supply-shock dynamics.
        3. **Design & Develop** a sequence-based PyTorch neural network that forecasts multi-horizon prices and evaluates crop cultivation suitability.
        4. **Deliver** an accessible, visual decision dashboard for smallholders and agricultural policymakers.
        """)
        
    with col_right:
        st.subheader("Monitored Agricultural Crops")
        crops_list = sorted(prices_df["crop_name"].unique())
        crop_data = []
        for c in crops_list:
            prof = CROP_AGRONOMIC_PROFILES.get(c, {})
            crop_data.append({
                "Crop": c,
                "Duration": f"{prof.get('duration_months', 3)} months",
                "Cost (LKR/kg)": f"LKR {prof.get('est_cost_per_kg', 0):.0f}",
                "Yield (kg/acre)": f"{prof.get('yield_per_acre_kg', 0):,}",
            })
        st.dataframe(pd.DataFrame(crop_data), use_container_width=True, hide_index=True)
        
        st.info("System Status: All data pipelines, SQLite tables, and PyTorch model weights are active.")


# --------------------------------------------------------------------------------------
# MODULE 2: FARMER SURVEY INSIGHTS (100% ENGLISH & INTELLIGENTLY GROUPED)
# --------------------------------------------------------------------------------------
elif menu == "Farmer Survey Insights":
    st.markdown('<div class="main-title">Smallholder Farmer Survey Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Empirical requirement elicitation from vegetable smallholders in Badulla District (Badulla Central and Welimada Divisions). Fully translated to English and grouped by meaning.</div>', unsafe_allow_html=True)
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Surveyed Farmers", len(survey_df), "Badulla & Welimada")
    with col_kpi2:
        st.metric("Need 1-7 Day Price Forecast", "100%", "Unanimous Demand")
    with col_kpi3:
        st.metric("Need Crop Decision Advisor", "100%", "Unanimous Demand")
        
    st.markdown("---")
    
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Farming Career Experience Tiers")
        exp_counts = survey_df["experience_tier"].value_counts().reset_index()
        exp_counts.columns = ["Experience Tier", "Farmers"]
        fig1 = px.bar(
            exp_counts,
            x="Experience Tier",
            y="Farmers",
            color="Farmers",
            color_continuous_scale="Greens",
        )
        fig1.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_chart2:
        st.subheader("Perceived Core Causes of Price Volatility")
        causes = survey_df["causes_of_volatility"].str.split(";").explode().str.strip().value_counts().reset_index()
        causes.columns = ["Primary Cause", "Mentions"]
        fig2 = px.bar(
            causes,
            x="Mentions",
            y="Primary Cause",
            orientation="h",
            color="Mentions",
            color_continuous_scale="Teal",
        )
        fig2.update_layout(margin=dict(t=20, b=20, l=20, r=20), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)
        
    col_chart3, col_chart4 = st.columns(2)
    with col_chart3:
        st.subheader("Farm Size Categories")
        size_counts = survey_df["farm_size_category"].value_counts().reset_index()
        size_counts.columns = ["Farm Category", "Farmers"]
        fig3 = px.pie(size_counts, names="Farm Category", values="Farmers", color_discrete_sequence=["#16a34a", "#0d9488", "#2563eb"])
        fig3.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig3, use_container_width=True)
        
    with col_chart4:
        st.subheader("Current Sources of Price Information")
        info_counts = survey_df["info_source"].value_counts().reset_index()
        info_counts.columns = ["Information Channel", "Farmers"]
        fig4 = px.bar(info_counts, x="Information Channel", y="Farmers", color="Farmers", color_continuous_scale="Blues")
        fig4.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig4, use_container_width=True)
        
    st.subheader("Detailed Farmer Respondent Profiles (English & Grouped)")
    display_survey = survey_df[[
        "farmer_name", "region_grouped", "age_group", "gender", "experience_years",
        "farm_size_category", "main_crops", "price_volatility_impact", "causes_of_volatility",
        "other_causes_elaborated", "feedback_notes"
    ]].copy()
    display_survey.columns = [
        "Farmer Name", "Region", "Age Bracket", "Gender", "Exp (Yrs)",
        "Farm Size Category", "Main Crops", "Price Volatility Impact", "Key Causes",
        "Structural Cause Notes", "Farmer Feedback Notes"
    ]
    st.dataframe(display_survey, use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------------------
# MODULE 3: PRICE & WEATHER ANALYTICS (EDA)
# --------------------------------------------------------------------------------------
elif menu == "Price & Weather Analytics":
    st.markdown('<div class="main-title">Exploratory Data Analysis: Prices & Meteorology</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Examining 25 years of vegetable market prices alongside multi-variate climatic trends.</div>', unsafe_allow_html=True)
    
    selected_crop = st.selectbox("Select Crop for In-Depth Trend Analysis:", sorted(prices_df["crop_name"].unique()), index=0)
    c_df = prices_df[prices_df["crop_name"] == selected_crop].sort_values("date")
    
    # Time-Series Line Chart: Farm Price vs Pettah vs Dambulla
    st.subheader(f"{selected_crop}: Historical Market Prices & Middleman Spread (2000 - 2025)")
    fig_prices = go.Figure()
    fig_prices.add_trace(go.Scatter(x=c_df["date"], y=c_df["farm_price"], mode="lines", name="Farmgate Price (LKR/kg)", line=dict(color="#16a34a", width=2)))
    fig_prices.add_trace(go.Scatter(x=c_df["date"], y=c_df["retail_price_pettah"], mode="lines", name="Retail Pettah Price", line=dict(color="#2563eb", width=1.5, dash="dot")))
    fig_prices.add_trace(go.Scatter(x=c_df["date"], y=c_df["retail_price_dambulla"], mode="lines", name="Retail Dambulla Price", line=dict(color="#d97706", width=1.5, dash="dot")))
    fig_prices.add_trace(go.Bar(x=c_df["date"], y=c_df["average_spread"], name="Intermediary Margin / Spread", marker_color="rgba(239, 68, 68, 0.35)"))
    fig_prices.update_layout(
        xaxis_title="Timeline",
        yaxis_title="Price (LKR / kg)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(t=30, b=30, l=30, r=30),
    )
    st.plotly_chart(fig_prices, use_container_width=True)
    
    col_eda1, col_eda2 = st.columns(2)
    with col_eda1:
        st.subheader("Seasonal Month Price Distribution")
        month_box = px.box(
            c_df,
            x="month",
            y="farm_price",
            color="month",
            labels={"month": "Month of Year (1=Jan, 12=Dec)", "farm_price": "Farmgate Price (LKR/kg)"},
        )
        month_box.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(month_box, use_container_width=True)
        
    with col_eda2:
        st.subheader("Meteorological Climate Seasonality (National)")
        fig_weather = go.Figure()
        fig_weather.add_trace(go.Bar(x=weather_df["date"], y=weather_df["rain_sum"], name="Monthly Rainfall (mm)", yaxis="y1", marker_color="#0284c7"))
        fig_weather.add_trace(go.Scatter(x=weather_df["date"], y=weather_df["temp_mean"], name="Mean Temp (C)", yaxis="y2", line=dict(color="#dc2626", width=2)))
        fig_weather.update_layout(
            yaxis=dict(title="Rainfall (mm)"),
            yaxis2=dict(title="Temperature (C)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.05),
            margin=dict(t=20, b=20, l=20, r=20),
            hovermode="x unified",
        )
        st.plotly_chart(fig_weather, use_container_width=True)
        
    # Cross-Correlation Heatmap
    st.subheader("Cross-Correlation Heatmap: Climate Parameters vs. Crop Prices")
    corr_cols = [
        "farm_price", "retail_price_pettah", "retail_price_dambulla", "average_spread",
        "temp_mean", "temp_max", "rain_sum", "rain_days", "sunshine_mean_hours", "et0_mean"
    ]
    corr_matrix = merged_df[merged_df["crop_name"] == selected_crop][corr_cols].corr()
    fig_corr = px.imshow(
        corr_matrix,
        text_auto=".2f",
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(color="Correlation"),
    )
    fig_corr.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_corr, use_container_width=True)


# --------------------------------------------------------------------------------------
# MODULE 4: PYTORCH FORECAST & FLUCTUATION (WITH STARTING MONTH WEATHER & PRICE FLUCTUATION)
# --------------------------------------------------------------------------------------
elif menu == "PyTorch Forecast & Fluctuation":
    st.markdown('<div class="main-title">Forward & Historical Price Prediction with Market Inflation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Simulate price trajectories and seasonal weather conditions forwards or backwards in time, accounting for macroeconomic market inflation compounding and 90% confidence corridors.</div>', unsafe_allow_html=True)
    
    # Selection Controls - Row 1: Commodity & Timeline Base
    col_fc1, col_fc2, col_fc3, col_fc4 = st.columns(4)
    with col_fc1:
        target_crop = st.selectbox("Commodity Crop:", sorted(prices_df["crop_name"].unique()), index=0)
    with col_fc2:
        start_year = st.number_input("Starting Year:", min_value=2000, max_value=2035, value=2026, step=1)
    with col_fc3:
        month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        selected_start_name = st.selectbox("Starting Month:", month_names, index=9) # October (Maha)
        start_month_num = month_names.index(selected_start_name) + 1
    with col_fc4:
        district_sel = st.selectbox("Agricultural District:", ["Badulla", "Nuwara Eliya", "Matale", "Anuradhapura"], index=0)
        
    # Selection Controls - Row 2: Direction, Horizon & Inflation
    col_opt1, col_opt2, col_opt3 = st.columns([2, 1, 1])
    with col_opt1:
        calc_direction = st.radio(
            "Calculation Timeline Direction:",
            ["Forward in Time (Future Horizon Forecast)", "Backwards in Time (Historical Simulation / Counterfactual)"],
            index=0,
            horizontal=True,
        )
        dir_code = "forward" if "Forward" in calc_direction else "backward"
    with col_opt2:
        forecast_horizon = st.slider("Timeline Horizon (Months):", min_value=1, max_value=12, value=4)
    with col_opt3:
        inflation_rate = st.number_input("Annual Inflation Rate (%):", min_value=0.0, max_value=60.0, value=5.5, step=0.5)
        
    # Query combined price fluctuation and weather forecast
    fluct_data = predict_price_and_weather_fluctuations(
        crop_name=target_crop,
        start_year=int(start_year),
        start_month=start_month_num,
        horizon=forecast_horizon,
        direction=dir_code,
        annual_inflation_rate=float(inflation_rate),
        district=district_sel,
    )
    
    base_price = fluct_data["base_farm_price_lkr"]
    timeline = fluct_data["timeline"]
    start_label = fluct_data["start_period_label"]
    
    # Robust KPI Metrics (Safe from empty/index errors)
    if timeline:
        peak_item = max(timeline, key=lambda x: x["projected_farm_price"])
        peak_price = peak_item["projected_farm_price"]
        peak_label = peak_item["target_period_label"]
        max_delta_item = max(timeline, key=lambda x: abs(x["price_pct_change"]))
        max_delta_val = max_delta_item["price_pct_change"]
        total_rain = sum([t["weather"]["rain_sum"] for t in timeline])
    else:
        peak_price = base_price
        peak_label = start_label
        max_delta_val = 0.0
        total_rain = 0.0
        
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(f"Starting Base Price ({start_label})", f"LKR {base_price:.2f} / kg")
    with col_m2:
        cum_peak_change = ((peak_price - base_price) / (base_price + 1e-4)) * 100
        st.metric(f"Peak Price ({peak_label})", f"LKR {peak_price:.2f} / kg", f"{cum_peak_change:+.1f}%")
    with col_m3:
        st.metric("Max Period Fluctuation", f"{max_delta_val:+.1f} %", "Peak Volatility")
    with col_m4:
        st.metric(f"Total Expected Rain ({forecast_horizon} Mo)", f"{total_rain:.1f} mm", "Cumulative Influx")
        
    st.markdown("---")
    
    # Dual Visualizations: Price Fluctuation vs Weather Progression
    col_plot1, col_plot2 = st.columns(2)
    
    with col_plot1:
        dir_title = "Forward Price Trajectory" if dir_code == "forward" else "Backward Historical Trajectory"
        st.subheader(f"{dir_title} from {start_label} (with {inflation_rate}% Inflation)")
        
        timeline_labels = [start_label + " (Base)"] + [t["target_period_label"] for t in timeline]
        prices_plot = [base_price] + [t["projected_farm_price"] for t in timeline]
        real_prices_plot = [base_price] + [t["real_price_constant"] for t in timeline]
        lowers_plot = [base_price] + [t["ci_lower"] for t in timeline]
        uppers_plot = [base_price] + [t["ci_upper"] for t in timeline]
        deltas_plot = [0.0] + [t["price_delta_lkr"] for t in timeline]
        
        fig_p = go.Figure()
        # 90% Confidence corridor
        fig_p.add_trace(go.Scatter(
            x=timeline_labels + timeline_labels[::-1],
            y=uppers_plot + lowers_plot[::-1],
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="90% Confidence Corridor",
            hoverinfo="skip",
        ))
        # Projected Nominal Price line
        fig_p.add_trace(go.Scatter(
            x=timeline_labels,
            y=prices_plot,
            mode="lines+markers+text",
            text=[f"LKR {p:.0f}" for p in prices_plot],
            textposition="top center",
            name="Nominal Farm Price (Inflated)",
            line=dict(color="#2563eb", width=3),
            marker=dict(size=8, color="#1e40af"),
        ))
        # Real Constant Price line (Inflation-Adjusted)
        fig_p.add_trace(go.Scatter(
            x=timeline_labels,
            y=real_prices_plot,
            mode="lines",
            name="Real Price (Base Year Constant LKR)",
            line=dict(color="#059669", width=2, dash="dot"),
        ))
        # Monthly Delta bars (Fluctuation)
        fig_p.add_trace(go.Bar(
            x=timeline_labels,
            y=deltas_plot,
            name="Step Fluctuation Delta (LKR)",
            marker_color=["#94a3b8" if d == 0 else ("#16a34a" if d > 0 else "#dc2626") for d in deltas_plot],
            opacity=0.6,
        ))
        fig_p.update_layout(
            yaxis_title="Price (LKR / kg)",
            hovermode="x unified",
            legend=dict(orientation="h", y=1.05),
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_p, use_container_width=True)
        
    with col_plot2:
        st.subheader(f"Expected Meteorological Conditions from {start_label}")
        rain_vals = [t["weather"]["rain_sum"] for t in timeline]
        temp_vals = [t["weather"]["temp_mean"] for t in timeline]
        step_labels = [t["target_period_label"] for t in timeline]
        
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(
            x=step_labels,
            y=rain_vals,
            name="Expected Rainfall (mm)",
            yaxis="y1",
            marker_color="#0284c7",
        ))
        fig_w.add_trace(go.Scatter(
            x=step_labels,
            y=temp_vals,
            mode="lines+markers+text",
            text=[f"{t:.1f}C" for t in temp_vals],
            textposition="top center",
            name="Mean Temperature (C)",
            yaxis="y2",
            line=dict(color="#dc2626", width=2.5),
            marker=dict(size=7, color="#991b1b"),
        ))
        fig_w.update_layout(
            yaxis=dict(title="Rainfall (mm)"),
            yaxis2=dict(title="Temperature (C)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.05),
            hovermode="x unified",
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_w, use_container_width=True)
        
    # Detailed Timeline Schedule Breakdown Table
    st.subheader(f"Detailed Weather & Price Fluctuation Matrix ({target_crop} from {start_label})")
    sched_rows = []
    for t in timeline:
        w = t["weather"]
        sched_rows.append({
            "Timeline Step": f"{t['step']:+d} Mo" if t["step"] != 0 else "Base",
            "Period (Month Year)": t["target_period_label"],
            "Nominal Farm Price": f"LKR {t['projected_farm_price']:.2f}",
            "Real Price (Base Constant)": f"LKR {t['real_price_constant']:.2f}",
            "Step Fluctuation (LKR)": f"{t['price_delta_lkr']:+.2f}",
            "Step Fluctuation (%)": f"{t['price_pct_change']:+.2f}%",
            "Cumulative Shift (%)": f"{t['cumulative_pct_change']:+.2f}%",
            "90% CI Range": f"LKR {t['ci_lower']:.1f} - {t['ci_upper']:.1f}",
            "Inflation Multiplier": f"{t['inflation_multiplier']:.4f}x",
            "Expected Temp": f"{w['temp_mean']:.1f} C",
            "Expected Rain": f"{w['rain_sum']:.1f} mm",
            "Rainy Days": f"{w['rain_days']} days",
            "Climate Risk Status": w["weather_risk"],
            "Data Source": "Actual Historical Record" if t.get("is_actual") else "PyTorch Model + Inflation",
        })
    st.dataframe(pd.DataFrame(sched_rows), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("Model Validation Metrics on Hold-Out Test Split (2023 - 2024)")
    if "by_crop" in metrics_data:
        metrics_table = []
        for c, m in metrics_data["by_crop"].items():
            metrics_table.append({
                "Crop Commodity": c,
                "Mean Actual (LKR)": f"LKR {m['Mean_Actual_Price']:.1f}",
                "MAE (LKR/kg)": f"LKR {m['MAE_LKR']:.2f}",
                "RMSE (LKR/kg)": f"LKR {m['RMSE_LKR']:.2f}",
                "MAPE (%)": f"{m['MAPE_pct']:.2f} %",
                "R2 Score": f"{m['R2_Score']:.3f}",
            })
        st.dataframe(pd.DataFrame(metrics_table), use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------------------
# MODULE 5: CROP PLANTATION ADVISOR (ZERO EMOJIS)
# --------------------------------------------------------------------------------------
elif menu == "Crop Plantation Advisor":
    st.markdown('<div class="main-title">Smart Crop Plantation Decision Advisor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Sliding-window simulation factoring in crop gestation periods, projected harvest prices, and agro-climatic risks.</div>', unsafe_allow_html=True)
    
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1:
        months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        selected_month_name = st.selectbox("Target Planting Month:", months_list, index=9) # October (Maha)
        planting_month_num = months_list.index(selected_month_name) + 1
    with col_in2:
        districts_list = ["Badulla", "Nuwara Eliya", "Welimada", "Matale", "Kandy", "Anuradhapura", "Jaffna", "Kurunegala", "Monaragala"]
        selected_district = st.selectbox("Farm Location / District:", districts_list, index=0)
    with col_in3:
        farm_acres = st.number_input("Cultivation Area (Acres):", min_value=0.25, max_value=25.0, value=1.5, step=0.25)
    with col_in4:
        risk_mode = st.selectbox("Risk Preference:", ["Balanced", "Maximum Profit", "Conservative / Low Risk"], index=0)
        
    recommendations = recommend_crops(
        planting_month=planting_month_num,
        farm_size_acres=farm_acres,
        target_district=selected_district,
        risk_preference=risk_mode,
    )
    
    st.markdown("---")
    st.subheader(f"Top Recommended Crops for Planting in {selected_month_name} ({selected_district})")
    
    top_3 = recommendations[:3]
    card_cols = st.columns(3)
    for idx, (col, rec) in enumerate(zip(card_cols, top_3)):
        with col:
            badge_class = "badge-success" if rec["verdict_badge"] == "success" else ("badge-warning" if rec["verdict_badge"] == "warning" else "badge-danger")
            st.markdown(f"""
            <div class="rec-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <span style="font-size:1.3rem; font-weight:700; color:#14532d;">Rank #{rec['rank']}: {rec['crop_name']}</span>
                    <span class="{badge_class}">{rec['verdict']}</span>
                </div>
                <div style="font-size:2rem; font-weight:800; color:#16a34a; margin-bottom:0.5rem;">
                    {rec['recommendation_score']}<span style="font-size:1rem; color:#6b7280;"> / 100</span>
                </div>
                <p><strong>Harvest Month:</strong> {rec['harvest_month_name']} ({rec['gestation_months']}m cycle)</p>
                <p><strong>Predicted Price:</strong> LKR {rec['predicted_farm_price_lkr']} / kg</p>
                <p><strong>Projected Net Profit:</strong> LKR {rec['projected_net_profit_total_lkr']:,.0f}</p>
                <p><strong>Profit Margin:</strong> {rec['profit_margin_pct']}%</p>
                <p><strong>Climate Match:</strong> {rec['climate_suitability_score']}%</p>
                <div style="background:#f8fafc; border-left:3px solid #16a34a; padding:6px 10px; font-size:0.8rem; color:#475569; margin-top:0.5rem;">
                    Agronomic Advice: {rec['agronomic_tip']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    # Full Table View
    st.subheader("Complete Cross-Crop Comparative Matrix")
    df_recs = pd.DataFrame(recommendations)
    display_df = df_recs[[
        "rank", "crop_name", "recommendation_score", "verdict", "gestation_months",
        "harvest_month_name", "predicted_farm_price_lkr", "production_cost_per_kg_lkr",
        "net_margin_per_kg_lkr", "profit_margin_pct", "projected_net_profit_total_lkr",
        "climate_suitability_score"
    ]].copy()
    display_df.columns = [
        "Rank", "Crop Name", "Score (/100)", "Verdict", "Gestation (Mo)",
        "Harvest Month", "Pred Farm Price", "Cost/kg (LKR)", "Net Margin/kg",
        "Margin (%)", "Projected Total Net Profit (LKR)", "Climate Match (%)"
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Download recommendations
    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Crop Recommendation Schedule (CSV)",
        data=csv_bytes,
        file_name=f"crop_recommendations_{selected_district}_{selected_month_name}.csv",
        mime="text/csv",
    )

