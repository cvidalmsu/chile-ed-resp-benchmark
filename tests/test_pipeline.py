import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_dataset import (
    canonical_feature,
    complete_prior_rolling_mean,
    expected_statistical_grid,
    lag_by_fixed_grid,
    measure_type,
    snake,
)

def test_snake_case_schema_names():
    assert snake("EstablecimientoCodigo") == "establecimiento_codigo"
    assert snake("SemanaEstadistica") == "semana_estadistica"

def test_canonical_features():
    assert canonical_feature("IRA Alta (J00-J06)", 4) == "ira_alta"
    assert canonical_feature("Influenza (J09-J11)", 5) == "influenza"
    assert canonical_feature("Neumonía (J12-J18)", 6) == "pneumonia"
    assert canonical_feature("Bronquitis/bronquiolitis aguda (J20-J21)", 7) == "bronchitis_bronchiolitis"
    assert canonical_feature("- Por covid-19, virus identificado U07.1", 35) is None
    assert canonical_feature("HOSPITALIZACIONES COVID-19, VIRUS IDENTIFICADO U07.1") is None

def test_measure_type_from_official_order_groups():
    assert measure_type(4) == "consultation"
    assert measure_type(33) == "hospitalization"

def test_expected_release_calendar():
    grid = expected_statistical_grid(2022, 2025)
    assert len(grid) == 209
    assert grid.groupby("anio")["semana_estadistica"].max().to_dict() == {
        2022: 52, 2023: 52, 2024: 52, 2025: 53,
    }
    assert grid["time_index"].tolist() == list(range(209))

def test_missing_values_do_not_collapse_lag_or_rolling_grid_positions():
    series = pd.Series([10.0, 20.0, np.nan, 40.0, 50.0, 60.0, 70.0])
    lag_1 = lag_by_fixed_grid(series, 1)
    rolling_3 = complete_prior_rolling_mean(series, 3)

    assert pd.isna(lag_1.iloc[3])  # t-1 is the missing third grid position, not the preceding observed value.
    assert pd.isna(rolling_3.iloc[5])  # The prior three grid positions include one missing value.
    assert rolling_3.iloc[6] == 50.0  # The complete prior window is [40, 50, 60].
