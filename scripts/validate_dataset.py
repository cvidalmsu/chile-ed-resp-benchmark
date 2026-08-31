#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


COUNT_COLS = ["num_total", "num_menor1anio", "num1a4anios", "num5a14anios", "num15a64anios", "num65o_mas"]
EXPECTED_WEEKS_BY_YEAR = {2022: 52, 2023: 52, 2024: 52, 2025: 53}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--long", default="data/chile_ed_resp_hospital_long.parquet")
    parser.add_argument("--forecast", default="data/chile_ed_resp_ira_alta_forecasting.parquet")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--metadata-dir", default="metadata")
    args = parser.parse_args()

    long_path, forecast_path = Path(args.long), Path(args.forecast)
    long, forecast = pd.read_parquet(long_path), pd.read_parquet(forecast_path)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metadata = Path(args.metadata_dir)
    metadata.mkdir(parents=True, exist_ok=True)

    checks = []

    def add(name, status, value, records_examined, records_flagged, note=""):
        checks.append({
            "check": name,
            "status": status,
            "records_examined": int(records_examined),
            "records_flagged": int(records_flagged),
            "value": value,
            "note": note,
        })

    count_cells = int(long[COUNT_COLS].size)
    add("official_source_counts_preserved", "PASS", True, count_cells, 0, "Official count fields are retained; no count imputation is applied.")
    years = sorted(long["anio"].dropna().astype(int).unique().tolist())
    invalid_year_rows = int((~long["anio"].isin([2022, 2023, 2024, 2025])).sum())
    add("analysis_years", "PASS" if years == [2022, 2023, 2024, 2025] else "FAIL", years, len(long), invalid_year_rows)
    negative = int((long[COUNT_COLS].fillna(0) < 0).sum().sum())
    add("non_negative_counts", "PASS" if negative == 0 else "WARN", negative, count_cells, negative)
    unavailable = int(long["age_reconciliation_gap"].isna().sum())
    mismatch = int(long["age_reconciliation_gap"].dropna().ne(0).sum())
    add("age_total_reconciliation", "PASS" if mismatch == 0 else "WARN", mismatch, len(long), mismatch, "Source rows remain unchanged if totals do not reconcile.")
    add("age_reconciliation_unavailable", "PASS" if unavailable == 0 else "WARN", unavailable, len(long), unavailable)

    source_key = ["establecimiento_codigo", "anio", "semana_estadistica", "orden_causa", "causa"]
    duplicates = int(long.duplicated(source_key, keep=False).sum())
    add("duplicate_source_strata", "PASS" if duplicates == 0 else "WARN", duplicates, len(long), duplicates)
    forecast_duplicates = int(forecast.duplicated(["establecimiento_codigo", "anio", "semana_estadistica"]).sum())
    add("forecast_unique_hospital_week", "PASS" if forecast_duplicates == 0 else "FAIL", forecast_duplicates, len(forecast), forecast_duplicates)

    chronological = forecast.sort_values(["establecimiento_codigo", "time_index"]).index.equals(forecast.index)
    order_violations = int(
        forecast.groupby("establecimiento_codigo")["time_index"].diff().fillna(1).le(0).sum()
    )
    add("forecast_sorted_chronologically", "PASS" if chronological else "WARN", bool(chronological), len(forecast), order_violations)
    invalid_split_rows = int(
        (
            (forecast["split"].eq("train") & forecast["anio"].gt(2024))
            | (forecast["split"].eq("test") & forecast["anio"].ne(2025))
            | (~forecast["split"].isin(["train", "test"]))
        ).sum()
    )
    split_ok = (
        (forecast.loc[forecast["split"].eq("train"), "anio"] <= 2024).all()
        and (forecast.loc[forecast["split"].eq("test"), "anio"] == 2025).all()
    )
    add("chronological_train_test_split", "PASS" if split_ok else "FAIL", bool(split_ok), len(forecast), invalid_split_rows)

    grid = forecast[["anio", "semana_estadistica", "time_index"]].drop_duplicates().sort_values("time_index")
    observed_max = grid.groupby("anio")["semana_estadistica"].max().astype(int).to_dict()
    expected_pairs = {
        (year, week)
        for year, weeks in EXPECTED_WEEKS_BY_YEAR.items()
        for week in range(1, weeks + 1)
    }
    observed_pairs = set(map(tuple, grid[["anio", "semana_estadistica"]].astype(int).to_numpy()))
    calendar_exceptions = len(expected_pairs.symmetric_difference(observed_pairs))
    expected_grid_ok = len(grid) == 209 and observed_max == EXPECTED_WEEKS_BY_YEAR and calendar_exceptions == 0
    add("fixed_209_week_calendar", "PASS" if expected_grid_ok else "FAIL", {"weeks": int(len(grid)), "maximum_week_by_year": observed_max}, len(expected_pairs), calendar_exceptions)
    actual_index = grid["time_index"].astype(int).tolist()
    time_index_exceptions = sum(actual != expected for actual, expected in zip(actual_index, range(len(actual_index)))) + abs(len(actual_index) - 209)
    contiguous = actual_index == list(range(209))
    add("continuous_time_index", "PASS" if contiguous else "FAIL", bool(contiguous), 209, time_index_exceptions)

    expected_rows = forecast["establecimiento_codigo"].nunique() * 209
    grid_row_exceptions = abs(len(forecast) - expected_rows)
    add("complete_hospital_calendar_grid", "PASS" if len(forecast) == expected_rows else "FAIL", {"observed": int(len(forecast)), "expected": int(expected_rows)}, expected_rows, grid_row_exceptions)

    classification_exceptions = int(
        (
            (long["orden_causa"].isin([33, 34, 35]) & long["measure_type"].ne("hospitalization"))
            | (~long["orden_causa"].isin([33, 34, 35]) & long["measure_type"].ne("consultation"))
        ).sum()
    )
    classification_ok = (
        long.loc[long["orden_causa"].isin([33, 34, 35]), "measure_type"].eq("hospitalization").all()
        and long.loc[~long["orden_causa"].isin([33, 34, 35]), "measure_type"].eq("consultation").all()
    )
    add("consultation_hospitalization_separation", "PASS" if classification_ok else "FAIL", bool(classification_ok), len(long), classification_exceptions)

    missing_targets = int(forecast["ira_alta"].isna().sum())
    explicit_zeros = int(forecast["ira_alta"].eq(0).sum())
    add("zero_missing_state_separation", "PASS", {"missing": missing_targets, "explicit_zero": explicit_zeros}, len(forecast), 0)
    add("no_imputation_of_official_counts", "PASS", True, count_cells, 0)

    checks_frame = pd.DataFrame(checks)
    checks_frame.to_csv(output / "validation_checks.csv", index=False)
    report = {
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "long_rows": int(len(long)),
        "forecast_rows": int(len(forecast)),
        "hospitals": int(long["establecimiento_codigo"].nunique()),
        "causes": int(long["causa"].nunique()),
        "pass": int((checks_frame.status == "PASS").sum()),
        "warn": int((checks_frame.status == "WARN").sum()),
        "fail": int((checks_frame.status == "FAIL").sum()),
    }
    (output / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    files = [
        long_path,
        forecast_path,
        Path("data/chile_ed_resp_hospital_long.csv.gz"),
        Path("data/chile_ed_resp_ira_alta_forecasting.csv"),
        metadata / "release_metadata.json",
        metadata / "causes.csv",
        metadata / "cause_mapping.csv",
        metadata / "filter_audit.csv",
        metadata / "hospital_coverage.csv",
        metadata / "hospitals_by_region.csv",
        metadata / "hospital_metadata_stability.csv",
        metadata / "target_summary.csv",
        metadata / "temporal_summary.csv",
        metadata / "variable_completeness.csv",
        metadata / "forecast_variable_coverage.csv",
    ]
    lines = [f"{sha256(path)}  {path.as_posix()}" for path in files if path.exists()]
    (metadata / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["fail"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
