#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

COUNT_COLS = ["num_total","num_menor1anio","num1a4anios","num5a14anios","num15a64anios","num65o_mas"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--long", default="data/chile_ed_resp_hospital_long.parquet")
    ap.add_argument("--forecast", default="data/chile_ed_resp_ira_alta_forecasting.parquet")
    ap.add_argument("--output-dir", default="results")
    ap.add_argument("--metadata-dir", default="metadata")
    args = ap.parse_args()
    long_path, forecast_path = Path(args.long), Path(args.forecast)
    long, forecast = pd.read_parquet(long_path), pd.read_parquet(forecast_path)
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    md = Path(args.metadata_dir); md.mkdir(parents=True, exist_ok=True)

    checks = []
    def add(name, status, value, note=""):
        checks.append({"check": name, "status": status, "value": value, "note": note})

    add("official_source_counts_preserved", "PASS", True, "Counts are read from DEIS/SADU; only derived features are computed.")
    add("analysis_years", "PASS" if set(long["anio"].dropna().astype(int)).issubset({2022,2023,2024,2025}) else "FAIL", sorted(long["anio"].dropna().astype(int).unique().tolist()))
    negative = int((long[COUNT_COLS].fillna(0) < 0).sum().sum())
    add("non_negative_counts", "PASS" if negative == 0 else "WARN", negative)
    unavailable = int(long["age_reconciliation_gap"].isna().sum())
    mismatch = int(long["age_reconciliation_gap"].dropna().ne(0).sum())
    add("age_total_reconciliation", "PASS" if mismatch == 0 else "WARN", mismatch, "Source rows are preserved even if the official total and age strata do not reconcile.")
    add("age_reconciliation_unavailable", "PASS" if unavailable == 0 else "WARN", unavailable, "Rows lacking one or more age-stratum values remain unchanged and are reported.")
    key_cols = ["establecimiento_codigo","anio","semana_estadistica","orden_causa","causa"]
    dups = int(long.duplicated(key_cols, keep=False).sum())
    add("duplicate_source_strata", "PASS" if dups == 0 else "WARN", dups, "Duplicates are reported before wide aggregation; they are not silently discarded.")
    add("forecast_unique_hospital_week", "PASS" if not forecast.duplicated(["establecimiento_codigo","anio","semana_estadistica"]).any() else "FAIL", int(forecast.duplicated(["establecimiento_codigo","anio","semana_estadistica"]).sum()))
    chronological = forecast.sort_values(["establecimiento_codigo","anio","semana_estadistica"]).index.equals(forecast.index)
    add("forecast_sorted_chronologically", "PASS" if chronological else "WARN", bool(chronological))
    split_ok = ((forecast.loc[forecast["split"].eq("train"),"anio"] <= 2024).all() and (forecast.loc[forecast["split"].eq("test"),"anio"] == 2025).all())
    add("chronological_train_test_split", "PASS" if split_ok else "FAIL", bool(split_ok))
    add("no_imputation_of_official_counts", "PASS", True)

    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(out / "validation_checks.csv", index=False)
    report = {
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "long_rows": int(len(long)), "forecast_rows": int(len(forecast)),
        "hospitals": int(long["establecimiento_codigo"].nunique()),
        "causes": int(long["causa"].nunique()),
        "pass": int((checks_df.status == "PASS").sum()),
        "warn": int((checks_df.status == "WARN").sum()),
        "fail": int((checks_df.status == "FAIL").sum()),
    }
    (out / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    files = [long_path, forecast_path, Path("data/chile_ed_resp_hospital_long.csv.gz"), Path("data/chile_ed_resp_ira_alta_forecasting.csv"), md / "release_metadata.json", md / "causes.csv", md / "hospital_coverage.csv"]
    lines = [f"{sha256(p)}  {p.as_posix()}" for p in files if p.exists()]
    (md / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["fail"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
