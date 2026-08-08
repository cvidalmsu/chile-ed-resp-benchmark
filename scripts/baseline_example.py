#!/usr/bin/env python3
"""Example only: seasonal-naive baseline for recommended hospitals.
No baseline metrics are hard-coded into the paper; run after building the real dataset.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

def main():
    p = Path("data/chile_ed_resp_ira_alta_forecasting.parquet")
    df = pd.read_parquet(p)
    rows = []
    for code, g in df[df["recommended_for_benchmark"]].groupby("establecimiento_codigo"):
        test = g[(g["split"] == "test") & g["ira_alta"].notna() & g["ira_alta_lag_52"].notna()].copy()
        if test.empty:
            continue
        y, pred = test["ira_alta"].astype(float), test["ira_alta_lag_52"].astype(float)
        mae = mean_absolute_error(y, pred)
        rmse = mean_squared_error(y, pred) ** 0.5
        denom = np.where(y.to_numpy() == 0, np.nan, y.to_numpy())
        mape = np.nanmean(np.abs((y.to_numpy()-pred.to_numpy())/denom))*100
        rows.append({"establecimiento_codigo": code, "n_test": len(test), "MAE": mae, "RMSE": rmse, "MAPE_percent": mape})
    out = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True)
    out.to_csv("results/seasonal_naive_baseline.csv", index=False)
    print(out.head(20).to_string(index=False))

if __name__ == "__main__":
    main()
