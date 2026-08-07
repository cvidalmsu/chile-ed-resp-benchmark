#!/usr/bin/env python3
"""Reproduce all figures used by the manuscript."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save(fig: plt.Figure, output: Path) -> None:
    fig.tight_layout()
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/chile_ed_resp_weekly_panel.csv")
    parser.add_argument("--metrics", default="results/baseline_metrics.csv")
    parser.add_argument("--predictions", default="results/baseline_predictions.csv")
    parser.add_argument("--output-dir", default="figures")
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(args.data)

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    weekly = data.groupby(["year", "epi_week"])["high_respiratory_infection"].mean().reset_index()
    for year, group in weekly.groupby("year"):
        ax.plot(group["epi_week"], group["high_respiratory_infection"], linewidth=1.8, label=str(year))
    ax.axvspan(10, 22, alpha=0.12)
    ax.set_xlabel("Epidemiological week")
    ax.set_ylabel("Mean synthetic high-respiratory demand")
    ax.set_title("Annual seasonal profiles across nine hospital sites")
    ax.legend(ncol=4, frameon=False)
    ax.grid(alpha=0.25)
    save(fig, out / "annual_seasonal_profiles.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    site_means = data.groupby("site_id")["high_respiratory_infection"].mean().sort_values()
    ax.bar(site_means.index, site_means.values)
    ax.set_xlabel("Synthetic hospital site")
    ax.set_ylabel("Mean weekly demand")
    ax.set_title("Demand-level heterogeneity encoded across site profiles")
    ax.grid(axis="y", alpha=0.25)
    save(fig, out / "site_mean_demand.png")

    corr_columns = ["high_respiratory_infection", "influenza", "pneumonia", "bronchial_crisis", "other_respiratory", "covid19_identified", "mean_temperature_c", "precipitation_mm"]
    corr = data[corr_columns].corr()
    fig, ax = plt.subplots(figsize=(7.8, 6.2))
    image = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(np.arange(len(corr_columns)), labels=[c.replace("_", " ") for c in corr_columns], rotation=50, ha="right")
    ax.set_yticks(np.arange(len(corr_columns)), labels=[c.replace("_", " ") for c in corr_columns])
    for i in range(len(corr_columns)):
        for j in range(len(corr_columns)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, shrink=0.82, label="Pearson correlation")
    ax.set_title("Correlation structure of the synthetic benchmark")
    save(fig, out / "correlation_matrix.png")

    metrics = pd.read_csv(args.metrics)
    fig, ax = plt.subplots(figsize=(7.7, 4.5))
    ax.bar(metrics["model"], metrics["mape_percent"])
    ax.set_ylabel("MAPE (%)")
    ax.set_title("Baseline forecasting performance on H09 test period")
    ax.tick_params(axis="x", rotation=18)
    ax.grid(axis="y", alpha=0.25)
    save(fig, out / "baseline_mape.png")

    preds = pd.read_csv(args.predictions)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.plot(preds["epi_week"], preds["observed"], marker="o", linewidth=2.0, label="Observed synthetic demand")
    model_columns = [column for column in preds.columns if column not in {"record_id", "year", "epi_week", "week_start", "observed"}]
    for column in model_columns:
        ax.plot(preds["epi_week"], preds[column], linewidth=1.4, label=column.replace("_", " "))
    ax.set_xlabel("Epidemiological week of 2025")
    ax.set_ylabel("Weekly demand")
    ax.set_title("Out-of-sample forecasts for the reference hospital profile")
    ax.legend(fontsize=7, frameon=False)
    ax.grid(alpha=0.25)
    save(fig, out / "reference_forecasts.png")


if __name__ == "__main__":
    main()
