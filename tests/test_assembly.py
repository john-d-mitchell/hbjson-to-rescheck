"""Tests for rescheck.assembly."""
import pytest
from rescheck.assembly import classify_layers, assembly_u_value

# SI R-value conversion factor
_SI_TO_IP = 5.678


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_layer(identifier, r_si):
    return {"identifier": identifier, "r_value": r_si}


# A typical wood-frame wall assembly (SI values)
# - OSB sheathing: structural, r_si = 0.10
# - Fiberglass batt R-21: cavity, r_si = 21 / 5.678 ≈ 3.699
# - Gypsum wallboard: structural, r_si = 0.06
_WALL_LAYERS = [
    make_layer("OSB_Sheathing", 0.10),
    make_layer("Fiberglass_Batt_R21", 21.0 / _SI_TO_IP),
    make_layer("GWB_Finish", 0.06),
]

# Wall with both cavity and continuous
_WALL_LAYERS_WITH_CI = [
    make_layer("OSB_Sheathing", 0.10),
    make_layer("Fiberglass_Batt_R13", 13.0 / _SI_TO_IP),
    make_layer("XPS_Rigid_R5", 5.0 / _SI_TO_IP),
    make_layer("GWB_Finish", 0.06),
]


# ---------------------------------------------------------------------------
# classify_layers
# ---------------------------------------------------------------------------

def test_classify_layers_cavity_only():
    cavity_r, cont_r = classify_layers(_WALL_LAYERS)
    assert cavity_r == pytest.approx(21.0, rel=1e-3)
    assert cont_r == pytest.approx(0.0)


def test_classify_layers_cavity_and_continuous():
    cavity_r, cont_r = classify_layers(_WALL_LAYERS_WITH_CI)
    assert cavity_r == pytest.approx(13.0, rel=1e-3)
    assert cont_r == pytest.approx(5.0, rel=1e-3)


def test_classify_layers_empty():
    cavity_r, cont_r = classify_layers([])
    assert cavity_r == pytest.approx(0.0)
    assert cont_r == pytest.approx(0.0)


def test_classify_layers_structural_excluded():
    layers = [
        make_layer("Concrete_Block", 0.5),
        make_layer("Stucco_Finish", 0.02),
    ]
    cavity_r, cont_r = classify_layers(layers)
    assert cavity_r == pytest.approx(0.0)
    assert cont_r == pytest.approx(0.0)


def test_classify_layers_rockwool():
    layers = [make_layer("Rockwool_Safe_n_Sound", 1.0)]
    cavity_r, cont_r = classify_layers(layers)
    assert cavity_r == pytest.approx(1.0 * _SI_TO_IP, rel=1e-3)
    assert cont_r == pytest.approx(0.0)


def test_classify_layers_polyiso():
    layers = [make_layer("Polyiso_Roof_Board_2in", 2.0)]
    cavity_r, cont_r = classify_layers(layers)
    assert cavity_r == pytest.approx(0.0)
    assert cont_r == pytest.approx(2.0 * _SI_TO_IP, rel=1e-3)


# ---------------------------------------------------------------------------
# assembly_u_value
# ---------------------------------------------------------------------------

def test_assembly_u_value_basic():
    # R_total_ip = (0.10 + 3.699 + 0.06) * 5.678 + 0.68 + 0.17
    r_si_total = 0.10 + (21.0 / _SI_TO_IP) + 0.06
    r_ip_total = r_si_total * _SI_TO_IP + 0.68 + 0.17
    expected_u = 1.0 / r_ip_total
    assert assembly_u_value(_WALL_LAYERS) == pytest.approx(expected_u, rel=1e-4)


def test_assembly_u_value_empty():
    # Empty layers → only air films: U = 1 / (0.68 + 0.17) = 1 / 0.85
    assert assembly_u_value([]) == pytest.approx(1.0 / 0.85, rel=1e-4)


def test_assembly_u_value_positive():
    u = assembly_u_value(_WALL_LAYERS_WITH_CI)
    assert u > 0.0
    assert u < 2.0  # sanity check — should be well below 2 BTU/h·ft²·°F
