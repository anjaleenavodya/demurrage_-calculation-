"""
Streamlit Community Cloud Root Launcher
Delegates directly to the Final Agri-MIS application.
Allows deploying either from repository root or subdirectory on Streamlit Cloud.
"""

import os
import sys
import runpy

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FINAL_DIR = os.path.join(ROOT_DIR, "Final")

if FINAL_DIR not in sys.path:
    sys.path.insert(0, FINAL_DIR)

TARGET_APP = os.path.join(FINAL_DIR, "src", "app.py")

if __name__ == "__main__" or "streamlit" in sys.modules:
    runpy.run_path(TARGET_APP, run_name="__main__")
