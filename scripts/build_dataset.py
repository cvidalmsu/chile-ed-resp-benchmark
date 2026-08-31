#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


DATASET_VERSION = "1.1.0"
EXPECTED = [
    "establecimiento_codigo", "establecimiento_glosa", "region_codigo", "region_glosa",
    "comuna_codigo", "comuna_glosa", "servicio_salud_codigo", "servicio_salud_glosa",
    "tipo_establecimiento", "dependencia_administrativa", "nivel_atencion", "tipo_urgencia",
    "latitud", "longitud", "nivel_complejidad", "anio", "semana_estadistica", "orden_causa",
    "causa", "num_total", "num_menor1anio", "num1a4anios", "num5a14anios",
    "num15a64anios", "num65o_mas",
]
AGE_COLS = [
    "num_menor1anio", "num1a4anios", "num5a14anios", "num15a64anios", "num65o_mas",
]
COUNT_COLS = ["num_total", *AGE_COLS]
KEY_COLS = ["establecimiento_codigo", "anio", "semana_estadistica"]
METADATA_COLS = [
    "establecimiento_glosa", "region_codigo", "region_glosa", "comuna_codigo", "comuna_glosa",
    "servicio_salud_codigo", "servicio_salud_glosa", "dependencia_administrativa",
    "nivel_atencion", "nivel_complejidad", "latitud", "longitud",
]

# The archived DEIS release coordinates for 2022--2025 contain 52, 52, 52,
# and 53 official statistical weeks, respectively. Fixing the release calendar
# prevents a nationally absent source record from silently shortening the grid.
EXPECTED_WEEKS_BY_YEAR = {2022: 52, 2023: 52, 2024: 52, 2025: 53}

# Official cause-order groups in the DEIS respiratory-emergency resource.
HOSPITALIZATION_CAUSE_ORDERS = {33, 34, 35}
CANONICAL_FEATURE_BY_ORDER = {
    4: "ira_alta",
    5: "influenza",
    6: "pneumonia",
    7: "bronchitis_bronchiolitis",
    9: "other_respiratory",
    10: "covid19_unidentified",
    11: "covid19_identified",
}
FORECAST_FEATURES = list(CANONICAL_FEATURE_BY_ORDER.values())


def snake(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def norm_text(value) -> str:
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower().strip()


def parse_coord(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def record_hash(row) -> str:
    raw = "|".join(str(row[c]) for c in ["establecimiento_codigo", "anio", "semana_estadistica", "orden_causa", "causa"])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def measure_type(order_cause) -> str:
    try:
        order = int(order_cause)
    except (TypeError, ValueError):
        return "unclassified"
    return "hospitalization" if order in HOSPITALIZATION_CAUSE_ORDERS else "consultation"


def canonical_feature(cause: str, order_cause=None) -> str | None:
    """Map consultation causes to forecasting fields without mixing measures."""
    normalized = norm_text(cause)
    if order_cause is not None and not pd.isna(order_cause):
        order = int(order_cause)
        if order in HOSPITALIZATION_CAUSE_ORDERS:
            return None
        return CANONICAL_FEATURE_BY_ORDER.get(order)
    if "hospitaliz" in normalized:
        return None
    if "ira alta" in normalized:
        return "ira_alta"
    if "influenza" in normalized:
        return "influenza"
    if "neumon" in normalized:
        return "pneumonia"
    if "bronquitis/bronquiolitis" in normalized or ("bronquitis" in normalized and "bronquiolitis" in normalized):
        return "bronchitis_bronchiolitis"
    if "covid-19" in normalized and "virus identificado" in normalized and "no identificado" not in normalized:
        return "covid19_identified"
    if "covid-19" in normalized and ("no identificado" in normalized or "virus no" in normalized):
        return "covid19_unidentified"
    if "otra" in normalized and "respir" in normalized:
        return "other_respiratory"
    return None


def expected_statistical_grid(start_year: int, end_year: int) -> pd.DataFrame:
    unsupported = [year for year in range(start_year, end_year + 1) if year not in EXPECTED_WEEKS_BY_YEAR]
    if unsupported:
        raise ValueError(
            "No fixed DEIS statistical-week calendar is registered for years "
            f"{unsupported}; update EXPECTED_WEEKS_BY_YEAR before extending the release."
        )
    rows = []
    time_index = 0
    for year in range(start_year, end_year + 1):
        weeks_in_year = EXPECTED_WEEKS_BY_YEAR[year]
        for week in range(1, weeks_in_year + 1):
            rows.append({
                "anio": year,
                "semana_estadistica": week,
                "weeks_in_statistical_year": weeks_in_year,
                "time_index": time_index,
            })
            time_index += 1
    return pd.DataFrame(rows)


def lag_by_fixed_grid(series: pd.Series, lag: int) -> pd.Series:
    """Return the value at the exact prior grid position without skipping NA rows."""
    return series.shift(lag)


def complete_prior_rolling_mean(series: pd.Series, window: int) -> pd.Series:
    """Use the preceding fixed-grid positions only and require all of them to be observed."""
    return series.shift(1).rolling(window, min_periods=window).mean()


def write_descriptive_metadata(
    source: pd.DataFrame,
    long: pd.DataFrame,
    wide: pd.DataFrame,
    causes: pd.DataFrame,
    filter_audit: pd.DataFrame,
    metadata_dir: Path,
) -> None:
    filter_audit.to_csv(metadata_dir / "filter_audit.csv", index=False)

    cause_mapping = causes.copy()
    cause_mapping["canonical_forecast_field"] = cause_mapping.apply(
        lambda row: canonical_feature(row["causa"], row["orden_causa"]), axis=1
    )
    cause_mapping["forecast_inclusion"] = np.where(
        cause_mapping["canonical_forecast_field"].notna(), "included", "excluded"
    )
    cause_mapping["exclusion_reason"] = ""
    cause_mapping.loc[cause_mapping["measure_type"].eq("hospitalization"), "exclusion_reason"] = "hospitalization measure"
    cause_mapping.loc[
        cause_mapping["measure_type"].eq("consultation")
        & cause_mapping["canonical_forecast_field"].isna(),
        "exclusion_reason",
    ] = "aggregate or non-target consultation category"
    cause_mapping.to_csv(metadata_dir / "cause_mapping.csv", index=False)

    completeness_rows = []
    for scope, frame, columns in [
        ("long", long, COUNT_COLS),
        ("forecast", wide, FORECAST_FEATURES),
    ]:
        for column in columns:
            observed = frame[column].notna()
            observed_n = int(observed.sum())
            missing_n = int((~observed).sum())
            zero_n = int(frame.loc[observed, column].eq(0).sum())
            completeness_rows.append({
                "artifact": scope,
                "variable": column,
                "rows": int(len(frame)),
                "observed_n": observed_n,
                "missing_n": missing_n,
                "missing_percent": 100 * missing_n / len(frame),
                "zero_n": zero_n,
                "zero_percent_of_observed": 100 * zero_n / observed_n if observed_n else np.nan,
            })
    pd.DataFrame(completeness_rows).to_csv(metadata_dir / "variable_completeness.csv", index=False)

    expected_weeks = int(wide["time_index"].nunique())
    variable_coverage_rows = []
    for column in FORECAST_FEATURES:
        observed_by_hospital = wide.groupby("establecimiento_codigo")[column].count()
        observed_n = int(wide[column].notna().sum())
        missing_n = int(wide[column].isna().sum())
        variable_coverage_rows.append({
            "variable": column,
            "rows": int(len(wide)),
            "observed_n": observed_n,
            "missing_n": missing_n,
            "missing_percent": 100 * missing_n / len(wide),
            "complete_209_week_hospitals": int(observed_by_hospital.eq(expected_weeks).sum()),
            "high_coverage_199_to_208_week_hospitals": int(observed_by_hospital.between(199, expected_weeks - 1).sum()),
            "below_199_week_hospitals": int(observed_by_hospital.lt(199).sum()),
            "minimum_observed_weeks": int(observed_by_hospital.min()),
            "maximum_observed_weeks": int(observed_by_hospital.max()),
        })
    pd.DataFrame(variable_coverage_rows).to_csv(
        metadata_dir / "forecast_variable_coverage.csv", index=False
    )

    latest_hospital = (
        long.sort_values(KEY_COLS).drop_duplicates("establecimiento_codigo", keep="last")
        [["establecimiento_codigo", "region_glosa"]]
    )
    recommendation = wide[["establecimiento_codigo", "recommended_for_benchmark"]].drop_duplicates("establecimiento_codigo")
    region = latest_hospital.merge(recommendation, on="establecimiento_codigo", how="left", validate="one_to_one")
    region_summary = (
        region.groupby("region_glosa", dropna=False)
        .agg(
            hospitals=("establecimiento_codigo", "nunique"),
            benchmark_recommended=("recommended_for_benchmark", "sum"),
        )
        .reset_index()
        .sort_values(["hospitals", "region_glosa"], ascending=[False, True])
    )
    region_summary.to_csv(metadata_dir / "hospitals_by_region.csv", index=False)

    target_rows = []
    frames = [("overall", wide)] + [(str(year), wide[wide["anio"].eq(year)]) for year in sorted(wide["anio"].unique())]
    for label, frame in frames:
        values = frame["ira_alta"].dropna().astype(float)
        target_rows.append({
            "period": label,
            "rows": int(len(frame)),
            "observed_n": int(len(values)),
            "missing_n": int(frame["ira_alta"].isna().sum()),
            "zero_n": int(values.eq(0).sum()),
            "mean": float(values.mean()),
            "sd": float(values.std(ddof=1)),
            "minimum": float(values.min()),
            "p25": float(values.quantile(0.25)),
            "median": float(values.median()),
            "p75": float(values.quantile(0.75)),
            "maximum": float(values.max()),
            "total": float(values.sum()),
        })
    pd.DataFrame(target_rows).to_csv(metadata_dir / "target_summary.csv", index=False)

    temporal = (
        wide.groupby(["time_index", "anio", "semana_estadistica"], as_index=False)
        .agg(
            observed_hospitals=("ira_alta", "count"),
            national_ira_alta_total=("ira_alta", lambda series: series.sum(min_count=1)),
            national_ira_alta_mean=("ira_alta", "mean"),
            national_ira_alta_median=("ira_alta", "median"),
        )
        .sort_values("time_index")
    )
    temporal.to_csv(metadata_dir / "temporal_summary.csv", index=False)

    metadata_stability_rows = []
    for column in METADATA_COLS:
        per_hospital = source.groupby("establecimiento_codigo")[column].nunique(dropna=False)
        metadata_stability_rows.append({
            "variable": column,
            "hospitals": int(len(per_hospital)),
            "hospitals_with_multiple_values": int(per_hospital.gt(1).sum()),
            "maximum_distinct_values_within_hospital": int(per_hospital.max()),
        })
    pd.DataFrame(metadata_stability_rows).to_csv(metadata_dir / "hospital_metadata_stability.csv", index=False)


def build(raw_path: Path, out_dir: Path, metadata_dir: Path, start_year: int, end_year: int):
    source = pd.read_parquet(raw_path)
    source.columns = [snake(column) for column in source.columns]

    expected_by_compact = {column.replace("_", ""): column for column in EXPECTED}
    aliases = {}
    for column in source.columns:
        compact = column.replace("_", "")
        if compact in expected_by_compact:
            aliases[column] = expected_by_compact[compact]
    source = source.rename(columns=aliases)
    missing = [column for column in EXPECTED if column not in source.columns]
    if missing:
        raise ValueError(f"Official schema changed; missing expected columns: {missing}. Found: {source.columns.tolist()}")

    source = source[EXPECTED].copy()
    for column in ["anio", "semana_estadistica", "orden_causa", *COUNT_COLS]:
        source[column] = pd.to_numeric(source[column], errors="coerce")

    mask_year = source["anio"].between(start_year, end_year, inclusive="both")
    mask_hospital = source["tipo_establecimiento"].map(norm_text).eq("hospital")
    mask_ueh = source["tipo_urgencia"].map(norm_text).str.contains("ueh", na=False)
    filter_audit = pd.DataFrame([
        {"step": 0, "filter": "Official Parquet snapshot", "rows": int(len(source)), "rows_removed_at_step": 0},
        {"step": 1, "filter": f"Statistical years {start_year}--{end_year}", "rows": int(mask_year.sum()), "rows_removed_at_step": int(len(source) - mask_year.sum())},
        {"step": 2, "filter": "tipo_establecimiento = Hospital", "rows": int((mask_year & mask_hospital).sum()), "rows_removed_at_step": int(mask_year.sum() - (mask_year & mask_hospital).sum())},
        {"step": 3, "filter": "tipo_urgencia contains UEH", "rows": int((mask_year & mask_hospital & mask_ueh).sum()), "rows_removed_at_step": int((mask_year & mask_hospital).sum() - (mask_year & mask_hospital & mask_ueh).sum())},
    ])

    long = source.loc[mask_year & mask_hospital & mask_ueh].copy()
    long["latitud"] = parse_coord(long["latitud"])
    long["longitud"] = parse_coord(long["longitud"])
    long["measure_type"] = long["orden_causa"].map(measure_type)
    long["age_sum"] = long[AGE_COLS].sum(axis=1, min_count=len(AGE_COLS))
    long["age_reconciliation_gap"] = long["num_total"] - long["age_sum"]
    long["statistical_period"] = (
        long["anio"].astype("Int64").astype(str)
        + "-W"
        + long["semana_estadistica"].astype("Int64").astype(str).str.zfill(2)
    )
    long["source_resource_id"] = "ae6c9887-106d-4e98-8875-40bf2b836041"
    long["record_id"] = long.apply(record_hash, axis=1)
    long["quality_flag"] = np.where(
        long["age_reconciliation_gap"].isna(),
        "age_reconciliation_unavailable",
        np.where(long["age_reconciliation_gap"].eq(0), "age_reconciled", "age_total_mismatch"),
    )
    long = long.sort_values([*KEY_COLS, "orden_causa", "causa"]).reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    long_parquet = out_dir / "chile_ed_resp_hospital_long.parquet"
    long_csv = out_dir / "chile_ed_resp_hospital_long.csv.gz"
    long.to_parquet(long_parquet, index=False)
    long.to_csv(long_csv, index=False, compression="gzip")

    causes = (
        long.groupby(["orden_causa", "causa", "measure_type"], dropna=False)
        .agg(rows=("num_total", "size"), total_reported=("num_total", "sum"))
        .reset_index()
        .sort_values(["measure_type", "orden_causa", "causa"])
    )
    causes.to_csv(metadata_dir / "causes.csv", index=False)

    consultations = long[long["measure_type"].eq("consultation")].copy()
    consultations["canonical_feature"] = consultations.apply(
        lambda row: canonical_feature(row["causa"], row["orden_causa"]), axis=1
    )
    selected = consultations[consultations["canonical_feature"].notna()].copy()

    values_wide = (
        selected.groupby([*KEY_COLS, "canonical_feature"], dropna=False, observed=True)["num_total"]
        .sum(min_count=1)
        .unstack("canonical_feature")
        .reset_index()
    )
    values_wide.columns.name = None

    meta_nunique = long.groupby(KEY_COLS)[METADATA_COLS].nunique(dropna=False)
    metadata_conflicts = int(meta_nunique.gt(1).any(axis=1).sum())
    if metadata_conflicts:
        raise ValueError(f"Found {metadata_conflicts} hospital-weeks with conflicting source metadata.")
    hospital_week_meta = long[[*KEY_COLS, *METADATA_COLS]].drop_duplicates(KEY_COLS)
    latest_hospital_meta = (
        hospital_week_meta.sort_values(KEY_COLS)
        .drop_duplicates("establecimiento_codigo", keep="last")
        [["establecimiento_codigo", *METADATA_COLS]]
    )

    expected_grid = expected_statistical_grid(start_year, end_year)
    observed_target_weeks = (
        selected.loc[selected["canonical_feature"].eq("ira_alta"), ["anio", "semana_estadistica"]]
        .drop_duplicates()
    )
    expected_pairs = set(map(tuple, expected_grid[["anio", "semana_estadistica"]].to_numpy()))
    observed_pairs = set(map(tuple, observed_target_weeks[["anio", "semana_estadistica"]].to_numpy()))
    unexpected_pairs = sorted(observed_pairs - expected_pairs)
    if unexpected_pairs:
        raise ValueError(f"Observed IRA Alta weeks outside the fixed release calendar: {unexpected_pairs}")
    missing_national_pairs = sorted(expected_pairs - observed_pairs)

    hospital_codes = latest_hospital_meta[["establecimiento_codigo"]].drop_duplicates().copy()
    hospital_codes["_join"] = 1
    expected_grid["_join"] = 1
    wide = (
        hospital_codes.merge(expected_grid, on="_join", how="inner")
        .drop(columns="_join")
        .merge(values_wide, on=KEY_COLS, how="left", validate="one_to_one")
        .merge(hospital_week_meta, on=KEY_COLS, how="left", validate="one_to_one")
    )
    wide["statistical_period"] = (
        wide["anio"].astype("Int64").astype(str)
        + "-W"
        + wide["semana_estadistica"].astype("Int64").astype(str).str.zfill(2)
    )

    for feature in FORECAST_FEATURES:
        if feature not in wide.columns:
            wide[feature] = np.nan

    wide = wide.sort_values(["establecimiento_codigo", "time_index"]).reset_index(drop=True)
    expected_week_count = len(expected_grid)
    coverage = (
        wide.assign(has_target=wide["ira_alta"].notna().astype(int))
        .groupby("establecimiento_codigo", as_index=False)
        .agg(observed_target_weeks=("has_target", "sum"))
    )
    coverage["expected_target_weeks"] = expected_week_count
    coverage["coverage_ratio"] = coverage["observed_target_weeks"] / expected_week_count
    coverage["recommended_for_benchmark"] = coverage["coverage_ratio"].ge(0.95)
    coverage = coverage.merge(
        latest_hospital_meta[["establecimiento_codigo", "establecimiento_glosa", "region_glosa", "servicio_salud_glosa"]],
        on="establecimiento_codigo",
        how="left",
        validate="one_to_one",
    )
    coverage.sort_values(
        ["recommended_for_benchmark", "coverage_ratio", "establecimiento_codigo"],
        ascending=[False, False, True],
    ).to_csv(metadata_dir / "hospital_coverage.csv", index=False)

    wide = wide.merge(
        coverage[["establecimiento_codigo", "observed_target_weeks", "expected_target_weeks", "coverage_ratio"]],
        on="establecimiento_codigo",
        how="left",
    )
    wide["recommended_for_benchmark"] = wide["coverage_ratio"].ge(0.95)
    wide["split"] = np.where(wide["anio"].le(end_year - 1), "train", "test")
    phase = (pd.to_numeric(wide["semana_estadistica"], errors="coerce") - 1) / wide["weeks_in_statistical_year"]
    wide["week_sin"] = np.sin(2 * np.pi * phase)
    wide["week_cos"] = np.cos(2 * np.pi * phase)

    grouped = wide.groupby("establecimiento_codigo", group_keys=False)["ira_alta"]
    for lag in [1, 2, 4]:
        wide[f"ira_alta_lag_{lag}"] = grouped.transform(
            lambda series, lag=lag: lag_by_fixed_grid(series, lag)
        )

    previous_year = wide[["establecimiento_codigo", "anio", "semana_estadistica", "ira_alta"]].copy()
    previous_year["anio"] = previous_year["anio"] + 1
    previous_year = previous_year.rename(columns={"ira_alta": "ira_alta_prev_year_same_week"})
    wide = wide.merge(
        previous_year,
        on=["establecimiento_codigo", "anio", "semana_estadistica"],
        how="left",
        validate="one_to_one",
    )
    wide = wide.sort_values(["establecimiento_codigo", "time_index"]).reset_index(drop=True)
    grouped = wide.groupby("establecimiento_codigo", group_keys=False)["ira_alta"]
    for window in [4, 12]:
        wide[f"ira_alta_rollmean_{window}"] = grouped.transform(
            lambda series, window=window: complete_prior_rolling_mean(series, window)
        )

    forecast_parquet = out_dir / "chile_ed_resp_ira_alta_forecasting.parquet"
    forecast_csv = out_dir / "chile_ed_resp_ira_alta_forecasting.csv"
    wide.to_parquet(forecast_parquet, index=False)
    wide.to_csv(forecast_csv, index=False)

    write_descriptive_metadata(source.loc[mask_year & mask_hospital & mask_ueh], long, wide, causes, filter_audit, metadata_dir)

    meta = {
        "dataset_title": "Chile-ED-Resp: Curated weekly hospital respiratory emergency-demand data for Chile",
        "version": DATASET_VERSION,
        "source": "DEIS/SADU official open-data Parquet",
        "source_resource_id": "ae6c9887-106d-4e98-8875-40bf2b836041",
        "analysis_period": [start_year, end_year],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_schema_columns": len(EXPECTED),
        "source_rows": int(len(source)),
        "long_rows": int(len(long)),
        "long_columns": int(long.shape[1]),
        "forecast_rows": int(len(wide)),
        "forecast_columns": int(wide.shape[1]),
        "hospitals_long": int(long["establecimiento_codigo"].nunique()),
        "hospitals_forecast": int(wide["establecimiento_codigo"].nunique()),
        "benchmark_recommended_hospitals": int(coverage["recommended_for_benchmark"].sum()),
        "expected_statistical_weeks": expected_week_count,
        "expected_weeks_by_year": {str(year): EXPECTED_WEEKS_BY_YEAR[year] for year in range(start_year, end_year + 1)},
        "national_missing_expected_ira_alta_weeks": [f"{year}-W{week:02d}" for year, week in missing_national_pairs],
        "hospital_week_metadata_conflicts": metadata_conflicts,
        "years": sorted(int(value) for value in long["anio"].dropna().unique()),
        "causes": int(long["causa"].nunique()),
        "license": "CC BY-NC 2.0 (derived data; source portal links Creative Commons Attribution-NonCommercial 2.0)",
        "imputation": "None",
        "smoothing": "None",
        "official_count_observations_preserved": True,
        "forecast_information_set": "Precomputed lag and rolling fields use observed target values through t-1 and are intended for rolling-origin one-week-ahead evaluation.",
        "notes": "The expected 209-week grid is fixed before hospital coverage is computed; absent records remain missing and explicit source zeros remain zero.",
    }
    (metadata_dir / "release_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return long, wide, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="raw/at_urg_respiratorio_semanal.parquet")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--metadata-dir", default="metadata")
    parser.add_argument("--start-year", type=int, default=2022)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()
    _, _, meta = build(Path(args.input), Path(args.output_dir), Path(args.metadata_dir), args.start_year, args.end_year)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
