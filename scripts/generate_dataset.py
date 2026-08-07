#!/usr/bin/env python3
"""Generate the deterministic Chile-ED-Resp synthetic benchmark dataset.

The generated observations are fully synthetic. They reproduce the temporal grid,
variable families, seasonal behavior, and correlation design documented in the
accompanying Data Descriptor, but they do not reproduce or disclose real hospital counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260805
DATASET_VERSION = "1.0.0"

SITES = [
    ("H01", "low_volume_rural", "north", 0.58),
    ("H02", "medium_regional", "north", 0.74),
    ("H03", "medium_regional", "central", 0.82),
    ("H04", "high_volume_urban", "central", 1.00),
    ("H05", "medium_regional", "central", 0.90),
    ("H06", "high_volume_urban", "central", 1.10),
    ("H07", "medium_regional", "south", 0.88),
    ("H08", "high_volume_urban", "south", 1.06),
    ("H09", "reference_tertiary", "central", 1.32),
]


def epidemiological_grid() -> list[tuple[int, int]]:
    grid: list[tuple[int, int]] = []
    for year in (2022, 2023, 2024):
        grid.extend((year, week) for week in range(1, 53))
    grid.extend((2025, week) for week in range(1, 37))
    if len(grid) != 192:
        raise RuntimeError("Unexpected temporal-grid length")
    return grid


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate_panel(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for site_id, profile, region, scale in SITES:
        previous_noise = 0.0
        for sequence, (year, epi_week) in enumerate(epidemiological_grid(), start=1):
            week_start = pd.Timestamp.fromisocalendar(year, epi_week, 1)
            temperature_baseline = {"north": 18.5, "central": 14.0, "south": 10.5}[region]
            temperature_amplitude = {"north": 4.5, "central": 6.2, "south": 5.7}[region]
            mean_temperature = temperature_baseline + temperature_amplitude * np.cos(2 * np.pi * (epi_week - 3) / 52) + rng.normal(0, 0.8)
            precipitation_baseline = {"north": 3.0, "central": 16.0, "south": 31.0}[region]
            precipitation = max(0.0, precipitation_baseline * (1 - np.cos(2 * np.pi * (epi_week - 3) / 52)) / 2 + rng.gamma(1.2, 2.0))
            winter_peak = np.exp(-0.5 * ((epi_week - 20) / 6.5) ** 2)
            late_year_wave = np.exp(-0.5 * ((epi_week - 39) / 7.5) ** 2)
            outbreak_intensity = max(0.0, 0.85 * winter_peak + 0.20 * late_year_wave + rng.normal(0, 0.05))
            influenza = max(0, rng.poisson(scale * (10 + 130 * winter_peak) * (1 + 0.08 * (year - 2022))))
            covid_baseline = {2022: 90, 2023: 48, 2024: 24, 2025: 14}[year]
            covid_identified = max(0, rng.poisson(scale * covid_baseline * (0.35 + 0.65 * np.exp(-0.5 * ((epi_week - 8) / 7) ** 2))))
            covid_unidentified = max(0, rng.poisson(max(1.0, 0.35 * covid_identified)))
            pneumonia = max(0, rng.poisson(scale * (22 + 75 * winter_peak + 10 * late_year_wave)))
            bronchial_crisis = max(0, rng.poisson(scale * (35 + 125 * winter_peak + 20 * late_year_wave)))
            other_respiratory = max(0, rng.poisson(scale * (105 + 180 * winter_peak + 40 * late_year_wave)))
            holiday_week = int(epi_week in {1, 15, 18, 38, 39, 52})
            school_vacation_week = int(epi_week in {27, 28, 29, 30})
            autoregressive_noise = 0.55 * previous_noise + rng.normal(0, 38 * scale)
            high_mean = scale * (290 + 360 * winter_peak + 80 * late_year_wave + 0.75 * influenza + 0.32 * bronchial_crisis + 0.18 * other_respiratory - 4.5 * (mean_temperature - temperature_baseline) + 25 * holiday_week - 20 * school_vacation_week) + autoregressive_noise
            high_respiratory = max(0, int(round(high_mean)))
            previous_noise = autoregressive_noise
            respiratory_total = high_respiratory + influenza + pneumonia + bronchial_crisis + other_respiratory + covid_identified + covid_unidentified
            age_proportions = np.array([0.055, 0.135, 0.190, 0.500, 0.120]) + np.array([0.010, 0.020, 0.015, -0.035, -0.010]) * winter_peak
            age_proportions = np.clip(age_proportions, 0.01, None)
            age_proportions = age_proportions / age_proportions.sum()
            age_counts = rng.multinomial(respiratory_total, age_proportions)
            data_quality_flag = "extreme_but_valid" if outbreak_intensity > 0.78 and high_respiratory > scale * 750 else "complete"
            recommended_split = "train" if year <= 2024 else "test"
            rows.append({
                "record_id": f"{site_id}-{year}-W{epi_week:02d}",
                "site_id": site_id,
                "site_profile": profile,
                "region_group": region,
                "sequence_index": sequence,
                "year": year,
                "epi_week": epi_week,
                "week_start": week_start.date().isoformat(),
                "high_respiratory_infection": high_respiratory,
                "influenza": influenza,
                "pneumonia": pneumonia,
                "bronchial_crisis": bronchial_crisis,
                "other_respiratory": other_respiratory,
                "covid19_identified": covid_identified,
                "covid19_unidentified": covid_unidentified,
                "respiratory_total": respiratory_total,
                "age_lt1": int(age_counts[0]),
                "age_1_4": int(age_counts[1]),
                "age_5_14": int(age_counts[2]),
                "age_15_64": int(age_counts[3]),
                "age_65_plus": int(age_counts[4]),
                "mean_temperature_c": round(float(mean_temperature), 2),
                "precipitation_mm": round(float(precipitation), 2),
                "holiday_week": holiday_week,
                "school_vacation_week": school_vacation_week,
                "outbreak_intensity": round(float(outbreak_intensity), 4),
                "data_quality_flag": data_quality_flag,
                "recommended_split": recommended_split,
                "is_synthetic": 1,
                "generator_seed": seed,
                "dataset_version": DATASET_VERSION,
            })
    return pd.DataFrame(rows)


def build_reference_features(panel: pd.DataFrame) -> pd.DataFrame:
    ref = panel.loc[panel["site_id"].eq("H09")].sort_values("sequence_index").copy()
    for lag in (1, 2, 4, 52):
        ref[f"high_resp_lag_{lag}"] = ref["high_respiratory_infection"].shift(lag)
    ref["high_resp_roll4_mean"] = ref["high_respiratory_infection"].shift(1).rolling(4).mean()
    ref["high_resp_roll8_mean"] = ref["high_respiratory_infection"].shift(1).rolling(8).mean()
    ref["sin_week"] = np.sin(2 * np.pi * ref["epi_week"] / 52)
    ref["cos_week"] = np.cos(2 * np.pi * ref["epi_week"] / 52)
    return ref


def write_metadata(output_dir: Path, panel: pd.DataFrame, reference: pd.DataFrame) -> None:
    metadata = {
        "dataset_name": "Chile-ED-Resp Benchmark",
        "version": DATASET_VERSION,
        "created_utc": "2026-08-05",
        "generator_seed": SEED,
        "synthetic": True,
        "description": "Deterministic synthetic weekly benchmark for respiratory emergency-demand forecasting across nine Chilean public-hospital profiles.",
        "temporal_coverage": {"start": "2022-W01", "end": "2025-W36", "weeks_per_site": 192},
        "spatial_design": {"sites": 9, "site_ids": sorted(panel["site_id"].unique().tolist())},
        "files": {
            "chile_ed_resp_weekly_panel.csv": {"rows": int(len(panel)), "columns": int(panel.shape[1])},
            "reference_hospital_features.csv": {"rows": int(len(reference)), "columns": int(reference.shape[1])},
        },
        "licenses": {"dataset": "CC BY 4.0", "code": "MIT"},
        "disclaimer": "All observations are synthetic and must not be interpreted as real hospital activity or used for clinical or operational decisions.",
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data", help="Output directory")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    panel = generate_panel()
    reference = build_reference_features(panel)
    panel_path = output_dir / "chile_ed_resp_weekly_panel.csv"
    reference_path = output_dir / "reference_hospital_features.csv"
    panel.to_csv(panel_path, index=False)
    panel.to_csv(output_dir / "chile_ed_resp_weekly_panel.csv.gz", index=False, compression="gzip")
    reference.to_csv(reference_path, index=False)
    write_metadata(output_dir, panel, reference)
    checksum_paths = [panel_path, output_dir / "chile_ed_resp_weekly_panel.csv.gz", reference_path, output_dir / "metadata.json"]
    checksum_text = "\n".join(f"{sha256(path)}  {path.name}" for path in checksum_paths) + "\n"
    (output_dir / "SHA256SUMS.txt").write_text(checksum_text, encoding="utf-8")
    print(f"Generated {len(panel):,} panel rows and {len(reference):,} reference-series rows in {output_dir}")


if __name__ == "__main__":
    main()
