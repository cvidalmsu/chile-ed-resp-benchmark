#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED = [
    "establecimiento_codigo","establecimiento_glosa","region_codigo","region_glosa",
    "comuna_codigo","comuna_glosa","servicio_salud_codigo","servicio_salud_glosa",
    "tipo_establecimiento","dependencia_administrativa","nivel_atencion","tipo_urgencia",
    "latitud","longitud","nivel_complejidad","anio","semana_estadistica","orden_causa",
    "causa","num_total","num_menor1anio","num1a4anios","num5a14anios","num15a64anios","num65o_mas"
]
AGE_COLS = ["num_menor1anio","num1a4anios","num5a14anios","num15a64anios","num65o_mas"]

def snake(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s

def norm_text(x) -> str:
    return unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode("ascii").lower().strip()

def parse_coord(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")

def record_hash(row) -> str:
    raw = "|".join(str(row[c]) for c in ["establecimiento_codigo","anio","semana_estadistica","orden_causa","causa"])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]

def canonical_feature(cause: str) -> str | None:
    c = norm_text(cause)
    if c.startswith("hospitalizaciones"):
        return None
    if "ira alta" in c:
        return "ira_alta"
    if "influenza" in c:
        return "influenza"
    if "neumon" in c:
        return "pneumonia"
    if "bronquitis/bronquiolitis" in c or ("bronquitis" in c and "bronquiolitis" in c):
        return "bronchitis_bronchiolitis"
    if "covid-19" in c and "virus identificado" in c and "no identificado" not in c:
        return "covid19_identified"
    if "covid-19" in c and ("no identificado" in c or "virus no" in c):
        return "covid19_unidentified"
    if "otra" in c and "respir" in c:
        return "other_respiratory"
    return None

def build(raw_path: Path, out_dir: Path, metadata_dir: Path, start_year: int, end_year: int):
    df = pd.read_parquet(raw_path)
    df.columns = [snake(c) for c in df.columns]
    # The official file has appeared with both CamelCase and already-cleaned
    # headings. Match columns by an underscore-insensitive canonical key so
    # changes such as NumMenor1Anio -> num_menor1_anio do not break the build.
    expected_by_compact = {re.sub(r"_", "", c): c for c in EXPECTED}
    aliases = {}
    for c in df.columns:
        compact = re.sub(r"_", "", c)
        if compact in expected_by_compact:
            aliases[c] = expected_by_compact[compact]
    df = df.rename(columns=aliases)
    missing = [c for c in EXPECTED if c not in df.columns]
    if missing:
        raise ValueError(f"Official schema changed; missing expected columns: {missing}. Found: {df.columns.tolist()}")

    # Keep only official source fields in a fixed order before deriving metadata.
    df = df[EXPECTED].copy()
    for c in ["anio","semana_estadistica","orden_causa","num_total",*AGE_COLS]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    mask_year = df["anio"].between(start_year, end_year, inclusive="both")
    hospital = df["tipo_establecimiento"].map(norm_text).eq("hospital")
    ueh = df["tipo_urgencia"].map(norm_text).str.contains("ueh", na=False)
    long = df.loc[mask_year & hospital & ueh].copy()

    long["latitud"] = parse_coord(long["latitud"])
    long["longitud"] = parse_coord(long["longitud"])
    long["measure_type"] = np.where(long["causa"].map(norm_text).str.startswith("hospitalizaciones"), "hospitalization", "consultation")
    long["age_sum"] = long[AGE_COLS].sum(axis=1, min_count=len(AGE_COLS))
    long["age_reconciliation_gap"] = long["num_total"] - long["age_sum"]
    long["epi_period"] = long["anio"].astype("Int64").astype(str) + "-W" + long["semana_estadistica"].astype("Int64").astype(str).str.zfill(2)
    long["source_resource_id"] = "ae6c9887-106d-4e98-8875-40bf2b836041"
    long["record_id"] = long.apply(record_hash, axis=1)
    long["quality_flag"] = np.where(
        long["age_reconciliation_gap"].isna(),
        "age_reconciliation_unavailable",
        np.where(long["age_reconciliation_gap"].eq(0), "age_reconciled", "age_total_mismatch"),
    )
    long = long.sort_values(["establecimiento_codigo","anio","semana_estadistica","orden_causa","causa"]).reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    long_parquet = out_dir / "chile_ed_resp_hospital_long.parquet"
    long_csv = out_dir / "chile_ed_resp_hospital_long.csv.gz"
    long.to_parquet(long_parquet, index=False)
    long.to_csv(long_csv, index=False, compression="gzip")

    # Cause inventory and duplicate diagnostics before any wide pivot.
    causes = (long.groupby(["orden_causa","causa","measure_type"], dropna=False)
              .agg(rows=("num_total","size"), total_reported=("num_total","sum"))
              .reset_index().sort_values(["measure_type","orden_causa","causa"]))
    causes.to_csv(metadata_dir / "causes.csv", index=False)

    cons = long[long["measure_type"].eq("consultation")].copy()
    cons["canonical_feature"] = cons["causa"].map(canonical_feature)
    selected = cons[cons["canonical_feature"].notna()].copy()

    # Pivot only on the stable hospital-week key. Descriptive metadata are
    # merged separately to avoid accidental Cartesian expansion when source
    # metadata contain missing values or administrative revisions.
    key_cols = ["establecimiento_codigo", "anio", "semana_estadistica"]
    values_wide = (selected.groupby(key_cols + ["canonical_feature"], dropna=False, observed=True)["num_total"]
                   .sum(min_count=1).unstack("canonical_feature").reset_index())
    values_wide.columns.name = None

    metadata_cols = ["establecimiento_glosa","region_codigo","region_glosa",
                     "comuna_codigo","comuna_glosa","servicio_salud_codigo","servicio_salud_glosa",
                     "dependencia_administrativa","nivel_atencion","nivel_complejidad","latitud","longitud"]
    # Preserve a coherent representative metadata record per hospital.
    hospital_meta = (long.sort_values(["establecimiento_codigo","anio","semana_estadistica"])
                     .drop_duplicates("establecimiento_codigo", keep="last")
                     [["establecimiento_codigo", *metadata_cols]])

    # Build an explicit national IRA-Alta week grid, then cross it with all
    # hospitals. This preserves missing hospital-weeks as missing rows so that
    # lag/rolling features reflect calendar sequence rather than merely the
    # previous observed record.
    target_weeks = (selected.loc[selected["canonical_feature"].eq("ira_alta"), ["anio","semana_estadistica"]]
                    .drop_duplicates().sort_values(["anio","semana_estadistica"]).reset_index(drop=True))
    if target_weeks.empty:
        raise ValueError("No IRA Alta observations were found in the selected official period.")
    hospital_codes = hospital_meta[["establecimiento_codigo"]].drop_duplicates().reset_index(drop=True)
    hospital_codes["_join"] = 1
    target_weeks["_join"] = 1
    wide = (hospital_codes.merge(target_weeks, on="_join", how="inner").drop(columns="_join")
            .merge(values_wide, on=key_cols, how="left", validate="one_to_one")
            .merge(hospital_meta, on="establecimiento_codigo", how="left", validate="many_to_one"))
    wide["epi_period"] = (wide["anio"].astype("Int64").astype(str) + "-W" +
                          wide["semana_estadistica"].astype("Int64").astype(str).str.zfill(2))

    for feat in ["ira_alta","influenza","pneumonia","bronchitis_bronchiolitis","other_respiratory","covid19_identified","covid19_unidentified"]:
        if feat not in wide.columns:
            wide[feat] = np.nan

    wide = wide.sort_values(["establecimiento_codigo","anio","semana_estadistica"]).reset_index(drop=True)
    national_weeks = len(target_weeks)
    coverage = (wide.assign(has_target=wide["ira_alta"].notna().astype(int))
                .groupby("establecimiento_codigo", as_index=False)
                .agg(observed_target_weeks=("has_target","sum")))
    coverage["coverage_ratio"] = coverage["observed_target_weeks"] / max(national_weeks, 1)
    coverage["recommended_for_benchmark"] = coverage["coverage_ratio"].ge(0.95)
    coverage = coverage.merge(
        hospital_meta[["establecimiento_codigo", "establecimiento_glosa", "region_glosa", "servicio_salud_glosa"]],
        on="establecimiento_codigo", how="left", validate="one_to_one"
    )
    coverage.sort_values(["recommended_for_benchmark", "coverage_ratio", "establecimiento_codigo"], ascending=[False, False, True]).to_csv(
        metadata_dir / "hospital_coverage.csv", index=False
    )
    wide = wide.merge(coverage[["establecimiento_codigo","observed_target_weeks","coverage_ratio"]], on="establecimiento_codigo", how="left")
    wide["recommended_for_benchmark"] = wide["coverage_ratio"].ge(0.95)
    wide["split"] = np.where(wide["anio"].le(end_year - 1), "train", "test")
    week = pd.to_numeric(wide["semana_estadistica"], errors="coerce")
    wide["week_sin"] = np.sin(2 * np.pi * week / 52.0)
    wide["week_cos"] = np.cos(2 * np.pi * week / 52.0)

    g = wide.groupby("establecimiento_codigo", group_keys=False)["ira_alta"]
    for lag in [1,2,4]:
        wide[f"ira_alta_lag_{lag}"] = g.shift(lag)
    # Seasonal lag: same statistical week in the previous year. This is more
    # robust than a row shift when a statistical year contains week 53.
    prev = wide[["establecimiento_codigo","anio","semana_estadistica","ira_alta"]].copy()
    prev["anio"] = prev["anio"] + 1
    prev = prev.rename(columns={"ira_alta":"ira_alta_lag_52"})
    wide = wide.merge(prev, on=["establecimiento_codigo","anio","semana_estadistica"], how="left", validate="one_to_one")
    wide = wide.sort_values(["establecimiento_codigo","anio","semana_estadistica"]).reset_index(drop=True)
    g = wide.groupby("establecimiento_codigo", group_keys=False)["ira_alta"]
    for win in [4,12]:
        wide[f"ira_alta_rollmean_{win}"] = g.transform(lambda series: series.shift(1).rolling(win, min_periods=win).mean())

    forecast_parquet = out_dir / "chile_ed_resp_ira_alta_forecasting.parquet"
    forecast_csv = out_dir / "chile_ed_resp_ira_alta_forecasting.csv"
    wide.to_parquet(forecast_parquet, index=False)
    wide.to_csv(forecast_csv, index=False)

    meta = {
        "dataset_title": "Chile-ED-Resp: Curated weekly hospital respiratory emergency-demand data for Chile",
        "version": "1.0.0",
        "source": "DEIS/SADU official open-data Parquet",
        "source_resource_id": "ae6c9887-106d-4e98-8875-40bf2b836041",
        "analysis_period": [start_year, end_year],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_schema_columns": len(EXPECTED),
        "long_rows": int(len(long)),
        "long_columns": int(long.shape[1]),
        "forecast_rows": int(len(wide)),
        "forecast_columns": int(wide.shape[1]),
        "hospitals_long": int(long["establecimiento_codigo"].nunique()),
        "hospitals_forecast": int(wide["establecimiento_codigo"].nunique()),
        "benchmark_recommended_hospitals": int(coverage["coverage_ratio"].ge(0.95).sum()),
        "years": sorted(int(x) for x in long["anio"].dropna().unique()),
        "causes": int(long["causa"].nunique()),
        "license": "CC BY-NC 2.0 (derived data; source portal links Creative Commons Attribution-NonCommercial 2.0)",
        "imputation": "None",
        "smoothing": "None",
        "official_count_observations_preserved": True,
        "notes": "All count variables in the curated long table are retained from the official source. Forecasting features are deterministic derivatives only."
    }
    (metadata_dir / "release_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return long, wide, meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="raw/at_urg_respiratorio_semanal.parquet")
    ap.add_argument("--output-dir", default="data")
    ap.add_argument("--metadata-dir", default="metadata")
    ap.add_argument("--start-year", type=int, default=2022)
    ap.add_argument("--end-year", type=int, default=2025)
    args = ap.parse_args()
    _, _, meta = build(Path(args.input), Path(args.output_dir), Path(args.metadata_dir), args.start_year, args.end_year)
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
