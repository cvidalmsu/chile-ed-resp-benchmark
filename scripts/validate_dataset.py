#!/usr/bin/env python3
"""Validate the structural, arithmetic, temporal, and statistical properties of the benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_SITES = 9
EXPECTED_WEEKS = 192
EXPECTED_ROWS = EXPECTED_SITES * EXPECTED_WEEKS
AGE_COLUMNS = ["age_lt1", "age_1_4", "age_5_14", "age_15_64", "age_65_plus"]
CAUSE_COLUMNS = ["high_respiratory_infection", "influenza", "pneumonia", "bronchial_crisis", "other_respiratory", "covid19_identified", "covid19_unidentified"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/chile_ed_resp_weekly_panel.csv")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()
    data = pd.read_csv(args.input, parse_dates=["week_start"])
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checks = {
        "row_count_is_1728": len(data) == EXPECTED_ROWS,
        "site_count_is_9": data["site_id"].nunique() == EXPECTED_SITES,
        "weeks_per_site_are_192": bool((data.groupby("site_id").size() == EXPECTED_WEEKS).all()),
        "record_id_is_unique": not data["record_id"].duplicated().any(),
        "site_week_is_unique": not data.duplicated(["site_id", "year", "epi_week"]).any(),
        "no_missing_values": int(data.isna().sum().sum()) == 0,
        "all_counts_nonnegative": bool((data[CAUSE_COLUMNS + AGE_COLUMNS + ["respiratory_total"]] >= 0).all().all()),
        "cause_sum_matches_total": bool((data[CAUSE_COLUMNS].sum(axis=1) == data["respiratory_total"]).all()),
        "age_sum_matches_total": bool((data[AGE_COLUMNS].sum(axis=1) == data["respiratory_total"]).all()),
        "synthetic_flag_is_one": bool(data["is_synthetic"].eq(1).all()),
        "train_test_partition_is_156_36": bool((data.groupby(["site_id", "recommended_split"]).size().unstack().loc[:, ["train", "test"]].values == [156, 36]).all()),
    }
    weekly_mean = data.groupby("epi_week")["high_respiratory_infection"].mean()
    peak_week = int(weekly_mean.idxmax())
    correlations = data[["high_respiratory_infection", "influenza", "bronchial_crisis", "other_respiratory", "covid19_identified", "mean_temperature_c"]].corr()["high_respiratory_infection"].round(4).to_dict()
    summary = {
        "dataset_rows": int(len(data)),
        "dataset_columns": int(data.shape[1]),
        "sites": int(data["site_id"].nunique()),
        "weeks_per_site": int(data.groupby("site_id").size().iloc[0]),
        "date_min": data["week_start"].min().date().isoformat(),
        "date_max": data["week_start"].max().date().isoformat(),
        "peak_epidemiological_week": peak_week,
        "quality_flag_counts": {k: int(v) for k, v in data["data_quality_flag"].value_counts().to_dict().items()},
        "correlations_with_target": correlations,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    (output_dir / "validation_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame([{"check": key, "passed": value} for key, value in checks.items()]).to_csv(output_dir / "validation_checks.csv", index=False)
    descriptive = data.groupby("site_id")[CAUSE_COLUMNS + ["respiratory_total"]].agg(["mean", "std", "min", "max"]).round(2)
    descriptive.to_csv(output_dir / "site_descriptive_statistics.csv")
    if not summary["all_checks_passed"]:
        failed = [key for key, value in checks.items() if not value]
        raise SystemExit(f"Validation failed: {failed}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
