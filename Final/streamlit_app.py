"""
Streamlit Community Cloud Entry Point
Sri Lanka Agriculture Management Information System (Agri-MIS)
"""

import os
import sys
import runpy

# Set project directory and ensure it's in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Path to the primary Streamlit application
APP_PATH = os.path.join(BASE_DIR, "src", "app.py")

if __name__ == "__main__" or "streamlit" in sys.modules:
    runpy.run_path(APP_PATH, run_name="__main__")
