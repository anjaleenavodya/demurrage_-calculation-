# Deploying Sri Lanka Agri-MIS to Streamlit Community Cloud

This guide provides the exact settings to deploy this application to [Streamlit Community Cloud](https://share.streamlit.io/).

---

## 1. File Structure Overview

The project is structured to support **both deployment scenarios** seamlessly:

```
demurrage_-calculation-/              <-- GitHub Repository Root
├── streamlit_app.py                  <-- Root Launcher (Option A)
├── requirements.txt                  <-- Direct dependencies for Streamlit Cloud
├── .streamlit/
│   └── config.toml                   <-- Theme & Server config
└── Final/
    ├── streamlit_app.py              <-- Subdirectory Entry Point (Option B)
    ├── requirements.txt              <-- Direct dependencies
    ├── requirements-lock.txt         <-- Pinned lockfile backup
    ├── .streamlit/
    │   └── config.toml
    ├── data_processed/
    │   ├── agriculture_mis.db        <-- SQLite database (included in git)
    │   └── crop_weather_monthly.csv
    ├── models/
    │   ├── pytorch_crop_lstm.pt      <-- PyTorch model checkpoint
    │   ├── feature_scaler.joblib     <-- Scaler weights
    │   └── model_metrics.json
    └── src/
        ├── app.py                    <-- Core Streamlit dashboard
        ├── model_pytorch.py          <-- Deep learning sequence inference
        ├── recommendation_engine.py  <-- Agro-climatic decision engine
        └── data_preprocessing.py     <-- Data pipeline
```

---

## 2. Streamlit Community Cloud Configuration

### Option A: Deploying from the Repository Root (Recommended)
When creating a **New app** on [share.streamlit.io](https://share.streamlit.io):

1. **Repository**: `anjaleenavodya/demurrage_-calculation-` (or your forked repository)
2. **Branch**: `main`
3. **Main file path**: `streamlit_app.py`
4. Click **Deploy!**

### Option B: Deploying with Subdirectory Path
If you prefer pointing directly to the `Final` directory:

1. **Repository**: `anjaleenavodya/demurrage_-calculation-`
2. **Branch**: `main`
3. **Main file path**: `Final/streamlit_app.py`
4. Click **Deploy!**

---

## 3. Key Deployment Safeguards Implemented

1. **Non-Loading Image Removed**:
   The dead Unsplash image in the sidebar has been removed from `Final/src/app.py`.
2. **Clean Direct Dependencies**:
   `requirements.txt` only specifies direct dependencies (`streamlit`, `torch`, `pandas`, `numpy`, `scikit-learn`, `joblib`, `plotly`, `openpyxl`, `matplotlib`, `seaborn`) with flexible `>=` version bounds to avoid OS-specific wheel compilation issues on Debian Linux containers.
3. **Dynamic Relative Path Resolution**:
   All dataset (`data_processed/`) and checkpoint (`models/`) paths are resolved dynamically using `os.path.abspath` relative to the code modules, ensuring reliable execution irrespective of the cloud working directory.
4. **Theme Configuration**:
   `.streamlit/config.toml` is configured with the green agricultural theme (`#16a34a`) and light background.
