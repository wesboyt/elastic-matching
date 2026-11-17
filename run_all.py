"""Reproduce everything: data, simulations, estimates, figures.

    python run_all.py            # all (about 15 minutes)
    python run_all.py --no-fetch # skip downloads if data/raw is populated
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "data_pipeline/fetch_data.py",
    "sims/s01_dating.py",
    "sims/s02_housing.py",
    "sims/s03_food.py",
    "sims/s04_healthcare.py",
    "data_pipeline/housing_extraction.py",
    "data_pipeline/monitor.py",
    "sims/s05_e2_method_check.py",
    "data_pipeline/e2_rate_gradient.py",
    "sims/s06_imbalance_shape.py",
    "data_pipeline/shortage.py",
    "sims/s07_housing_history.py",
    "data_pipeline/metro_shortage.py",
    "data_pipeline/fixed_rate_data.py",
    "sims/s08_fixed_rate.py",
    "sims/s09_financing_regimes.py",
    "data_pipeline/housing_growth_data.py",
    "data_pipeline/generations.py",
]

if __name__ == "__main__":
    for step in STEPS:
        if "--no-fetch" in sys.argv and "fetch" in step:
            continue
        print(f"\n=== {step}")
        subprocess.run([sys.executable, "-W", "ignore", str(ROOT / step)], check=True, cwd=ROOT)
