import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_dataset import snake, canonical_feature

def test_snake_case_schema_names():
    assert snake("EstablecimientoCodigo") == "establecimiento_codigo"
    assert snake("SemanaEstadistica") == "semana_estadistica"

def test_canonical_features():
    assert canonical_feature("IRA Alta (J00-J06)") == "ira_alta"
    assert canonical_feature("Influenza (J09-J11)") == "influenza"
    assert canonical_feature("Neumonía (J12-J18)") == "pneumonia"
    assert canonical_feature("Bronquitis/bronquiolitis aguda (J20-J21)") == "bronchitis_bronchiolitis"
    assert canonical_feature("HOSPITALIZACIONES COVID-19, VIRUS IDENTIFICADO U07.1") is None
