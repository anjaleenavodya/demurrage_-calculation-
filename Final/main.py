"""
Sri Lanka Agriculture Management Information System (MIS)
Main Entry Point & Pipeline Orchestrator

Usage:
    python main.py --preprocess       Run data cleaning, weather aggregation & SQLite creation
    python main.py --train            Train PyTorch sequence model (BiLSTM + Attention)
    python main.py --evaluate         Evaluate saved PyTorch model on out-of-sample test set
    python main.py --recommend        Run crop plantation decision recommendation engine
    python main.py --export-powerbi   Generate Star-Schema CSVs and scripts for Power BI
    python main.py --app              Launch the Streamlit interactive web application
    python main.py --all              Execute the end-to-end pipeline and launch the web app
"""

import os
import sys
import argparse
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
VENV_STREAMLIT = os.path.join(PROJECT_ROOT, ".venv", "bin", "streamlit")


def run_preprocess():
    print("\n=======================================================")
    print("  STEP 1: DATA PREPROCESSING & DATABASE PIPELINE")
    print("=======================================================")
    from src.data_preprocessing import run_preprocessing_pipeline
    return run_preprocessing_pipeline()


def run_train(epochs: int = 35):
    print("\n=======================================================")
    print("  STEP 2: PYTORCH TIME-SERIES MODEL TRAINING")
    print("=======================================================")
    from src.model_pytorch import train_model
    return train_model(epochs=epochs)


def run_evaluate():
    print("\n=======================================================")
    print("  STEP 3: PYTORCH MODEL EVALUATION")
    print("=======================================================")
    from src.model_pytorch import evaluate_saved_model
    return evaluate_saved_model()


def run_recommend(month: int = 10, district: str = "Badulla", acres: float = 1.5, risk: str = "Balanced"):
    print("\n=======================================================")
    print(f"  STEP 4: CROP PLANTATION ADVISOR ({district} - Month {month})")
    print("=======================================================")
    from src.recommendation_engine import recommend_crops
    recs = recommend_crops(planting_month=month, farm_size_acres=acres, target_district=district, risk_preference=risk)
    print(f"\nTop Recommendations for Planting in Month {month} ({district}):")
    for r in recs[:3]:
        print(f"  #{r['rank']} {r['crop_name']:<12} Score: {r['recommendation_score']}/100 [{r['verdict']}]")
        print(f"      Harvest Month: {r['harvest_month_name']} (Cycle: {r['gestation_months']}m)")
        print(f"      Pred Price: LKR {r['predicted_farm_price_lkr']} | Exp Net Profit: LKR {r['projected_net_profit_total_lkr']:,.0f} (Margin: {r['profit_margin_pct']}%)")
        print(f"      Agro-Climatic Match: {r['climate_suitability_score']}%")
    return recs


def run_export_powerbi():
    print("\n=======================================================")
    print("  STEP 5: GENERATE POWER BI ASSETS & STAR-SCHEMA TABLES")
    print("=======================================================")
    from src.powerbi_export import generate_powerbi_tables
    return generate_powerbi_tables()


def run_streamlit_app():
    print("\n=======================================================")
    print("  LAUNCHING STREAMLIT APPLICATION (http://localhost:8501)")
    print("=======================================================")
    app_path = os.path.join(PROJECT_ROOT, "src", "app.py")
    cmd = [VENV_STREAMLIT if os.path.exists(VENV_STREAMLIT) else "streamlit", "run", app_path]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStreamlit application terminated by user.")


def interactive_menu():
    print("\n" + "=" * 60)
    print("  SRI LANKA AGRI-MIS: PRICE FORECAST & CROP ADVISOR")
    print("=" * 60)
    print("  [1] Preprocess Data & Build SQLite Database")
    print("  [2] Train PyTorch BiLSTM Sequence Model")
    print("  [3] Evaluate Saved Model & Display Metrics")
    print("  [4] Run Crop Plantation Recommendation Engine")
    print("  [5] Launch Streamlit Interactive Web Application")
    print("  [6] Run Full End-to-End Pipeline & Launch App")
    print("  [0] Exit")
    print("=" * 60)
    
    choice = input("Enter choice [0-6]: ").strip()
    if choice == "1":
        run_preprocess()
    elif choice == "2":
        run_train()
    elif choice == "3":
        run_evaluate()
    elif choice == "4":
        m = int(input("Enter planting month (1-12, default 10): ").strip() or "10")
        d = input("Enter district (default Badulla): ").strip() or "Badulla"
        run_recommend(month=m, district=d)
    elif choice == "5":
        run_streamlit_app()
    elif choice == "6":
        run_preprocess()
        run_train()
        run_streamlit_app()
    elif choice == "0":
        print("Exiting. Goodbye!")
    else:
        print("Invalid choice.")


def main():
    parser = argparse.ArgumentParser(description="Sri Lanka Agriculture MIS Orchestrator")
    parser.add_argument("--preprocess", action="store_true", help="Run data preprocessing and create SQLite DB")
    parser.add_argument("--train", action="store_true", help="Train PyTorch sequence model")
    parser.add_argument("--epochs", type=int, default=35, help="Number of training epochs")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate model performance")
    parser.add_argument("--recommend", action="store_true", help="Generate crop recommendations")
    parser.add_argument("--month", type=int, default=10, help="Planting month (1-12) for recommendation")
    parser.add_argument("--district", type=str, default="Badulla", help="District for recommendation")
    parser.add_argument("--acres", type=float, default=1.5, help="Farm size in acres")
    parser.add_argument("--export-powerbi", action="store_true", help="Export Star-Schema tables for Power BI")
    parser.add_argument("--app", action="store_true", help="Launch Streamlit web application")
    parser.add_argument("--all", action="store_true", help="Run full pipeline and launch Streamlit app")
    
    args = parser.parse_args()
    
    # If no flags passed, invoke interactive menu
    if not any([args.preprocess, args.train, args.evaluate, args.recommend, args.export_powerbi, args.app, args.all]):
        interactive_menu()
        return
        
    if args.all:
        run_preprocess()
        run_train(epochs=args.epochs)
        run_export_powerbi()
        run_streamlit_app()
        return
        
    if args.preprocess:
        run_preprocess()
    if args.train:
        run_train(epochs=args.epochs)
    if args.evaluate:
        run_evaluate()
    if args.recommend:
        run_recommend(month=args.month, district=args.district, acres=args.acres)
    if args.export_powerbi:
        run_export_powerbi()
    if args.app:
        run_streamlit_app()


if __name__ == "__main__":
    main()
