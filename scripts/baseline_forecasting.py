#!/usr/bin/env python3
"""Run deterministic baseline forecasts on the reference hospital profile (H09)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.statespace.sarimax import SARIMAX


def metric_row(model: str, observed: np.ndarray, predicted: np.ndarray) -> dict[str, float | str]:
    return {
        "model": model,
        "rmse": float(np.sqrt(mean_squared_error(observed, predicted))),
        "mae": float(mean_absolute_error(observed, predicted)),
        "mape_percent": float(np.mean(np.abs((observed - predicted) / np.maximum(observed, 1))) * 100),
        "r2": float(r2_score(observed, predicted)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/chile_ed_resp_weekly_panel.csv")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(args.input)
    ref = data.loc[data["site_id"].eq("H09")].sort_values("sequence_index").reset_index(drop=True)
    train = ref.iloc[:156].copy()
    test = ref.iloc[156:].copy()
    target = "high_respiratory_infection"
    exogenous = ["influenza", "covid19_identified", "mean_temperature_c", "holiday_week"]
    observed = test[target].to_numpy(dtype=float)
    predictions: dict[str, np.ndarray] = {}
    predictions["Seasonal naive (lag 52)"] = ref[target].shift(52).iloc[156:].to_numpy(dtype=float)
    sarima = SARIMAX(train[target], order=(1, 1, 1), seasonal_order=(1, 1, 0, 52), enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=100)
    predictions["SARIMA(1,1,1)(1,1,0)[52]"] = sarima.get_forecast(steps=len(test)).predicted_mean.to_numpy(dtype=float)
    sarimax = SARIMAX(train[target], exog=train[exogenous], order=(1, 1, 1), seasonal_order=(1, 1, 0, 52), enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=100)
    predictions["SARIMAX + exogenous"] = sarimax.get_forecast(steps=len(test), exog=test[exogenous]).predicted_mean.to_numpy(dtype=float)
    metrics = pd.DataFrame([metric_row(name, observed, values) for name, values in predictions.items()]).round({"rmse": 2, "mae": 2, "mape_percent": 2, "r2": 4})
    metrics.to_csv(output_dir / "baseline_metrics.csv", index=False)
    prediction_frame = test[["record_id", "year", "epi_week", "week_start", target]].rename(columns={target: "observed"}).copy()
    for name, values in predictions.items():
        safe_name = name.lower().replace(" ", "_").replace("+", "plus").replace("(", "").replace(")", "").replace(",", "").replace("[", "").replace("]", "").replace("/", "_")
        prediction_frame[safe_name] = np.round(values, 3)
    prediction_frame.to_csv(output_dir / "baseline_predictions.csv", index=False)
    fit_metadata = {
        "train_rows": len(train),
        "test_rows": len(test),
        "target": target,
        "exogenous_variables": exogenous,
        "sarima_aic": float(sarima.aic),
        "sarimax_aic": float(sarimax.aic),
    }
    (output_dir / "baseline_fit_metadata.json").write_text(json.dumps(fit_metadata, indent=2), encoding="utf-8")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
