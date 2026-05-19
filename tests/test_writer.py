"""Tests for rescheck.writer."""
import xml.etree.ElementTree as ET
import pytest

from rescheck.envelope import EnvelopeData, WallData, RoofData, FloorData, WindowData, DoorData
from rescheck.writer import write_rxl, _glazing_type, _bool_str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NS = "http://energycode.pnl.gov/ns/ResCheckBuildingSchema"


def _tag(name):
    return "{%s}%s" % (_NS, name)


def _make_simple_envelope():
    wall = WallData(
        gross_area_ft2=322.92,
        u_value=0.065,
        cavity_r=21.0,
        continuous_r=0.0,
        orientation="FRONT",
        is_below_grade=False,
        wall_height_ft=9.84,
    )
    wall.windows.append(WindowData(
        area_ft2=32.29,
        u_value=0.28,
        shgc=0.40,
        orientation="FRONT",
        height_ft=4.92,
    ))
    roof = RoofData(
        gross_area_ft2=1076.39,
        u_value=0.025,
        cavity_r=38.0,
        continuous_r=0.0,
        roof_type="WOOD_CATHEDRAL",
    )
    floor = FloorData(
        gross_area_ft2=1076.39,
        cavity_r=19.0,
        floor_type="ALL_WOOD_JOIST_TRUSS_FLOOR",
    )
    return EnvelopeData(
        walls=[wall],
        roofs=[roof],
        floors=[floor],
        conditioned_floor_area_ft2=1076.39,
    )


_METADATA = {
    "project": {
        "title": "Test House",
        "address": "123 Main St",
        "city": "Woodstock",
        "state": "NY",
        "zip": "12498",
    },
    "owner": {"name": "Jane Smith"},
    "location": {
        "state": "New York",
        "city": "Woodstock (Ulster)",
    },
    "building": {
        "front_door_faces": "S",
        "construction_type": "SINGLE_FAMILY",
        "project_type": "NEW_CONSTRUCTION",
        "iecc_code": "IECC2021",
        "compliance_mode": "UA",
        "duct_location": "CONDITIONED_SPACE_ONLY",
        "all_electric": True,
        "has_heat_pump": True,
    },
}


# ---------------------------------------------------------------------------
# _glazing_type
# ---------------------------------------------------------------------------

def test_glazing_type_triple():
    assert _glazing_type(0.18) == "TRIPLE"
    assert _glazing_type(0.22) == "TRIPLE"


def test_glazing_type_double():
    assert _glazing_type(0.23) == "DOUBLE"
    assert _glazing_type(0.32) == "DOUBLE"


def test_glazing_type_single():
    assert _glazing_type(0.33) == "SINGLE"
    assert _glazing_type(1.0) == "SINGLE"


# ---------------------------------------------------------------------------
# _bool_str
# ---------------------------------------------------------------------------

def test_bool_str_true():
    assert _bool_str(True) == "true"
    assert _bool_str(1) == "true"


def test_bool_str_false():
    assert _bool_str(False) == "false"
    assert _bool_str(0) == "false"
    assert _bool_str(None) == "false"


# ---------------------------------------------------------------------------
# write_rxl output validity
# ---------------------------------------------------------------------------

def test_write_rxl_returns_string():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    assert isinstance(result, str)


def test_write_rxl_is_valid_xml():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    # Should parse without exception
    root = ET.fromstring(result)
    assert root is not None


def test_write_rxl_namespace():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    assert root.tag == _tag("building")


def test_write_rxl_project_type():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    el = root.find(_tag("projectType"))
    assert el is not None
    assert el.text == "NEW_CONSTRUCTION"


def test_write_rxl_conditioned_floor_area():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    el = root.find(_tag("conditionedFloorArea"))
    assert el is not None
    assert float(el.text) == pytest.approx(1076.39, rel=1e-3)


def test_write_rxl_all_electric_true():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    el = root.find(_tag("allElectric"))
    assert el is not None
    assert el.text == "true"


def test_write_rxl_has_heat_pump_true():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    el = root.find(_tag("hasHeatPump"))
    assert el is not None
    assert el.text == "true"


def test_write_rxl_location():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    loc = root.find(_tag("location"))
    assert loc is not None
    assert loc.find(_tag("state")).text == "New York"
    assert "Woodstock" in loc.find(_tag("city")).text


def test_write_rxl_infiltration():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    infil = root.find(_tag("infiltration"))
    assert infil is not None
    ach_el = infil.find(_tag("loadsAch"))
    assert ach_el is not None
    assert float(ach_el.text) == pytest.approx(0.5, rel=1e-3)


def test_write_rxl_control_code():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    ctrl = root.find(_tag("control"))
    assert ctrl is not None
    assert ctrl.find(_tag("code")).text == "IECC2021"
    assert ctrl.find(_tag("complianceMode")).text == "UA"


def test_write_rxl_envelope_present():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    envelope_el = root.find(_tag("envelope"))
    assert envelope_el is not None


def test_write_rxl_above_ground_wall():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    envelope_el = root.find(_tag("envelope"))
    walls_el = envelope_el.find(_tag("aboveGroundWalls"))
    assert walls_el is not None
    ag_el = walls_el.find(_tag("agWall"))
    assert ag_el is not None
    assert ag_el.find(_tag("relOrientation")).text == "FRONT"
    assert float(ag_el.find(_tag("grossArea")).text) == pytest.approx(322.92, rel=1e-3)


def test_write_rxl_window_in_wall():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    envelope_el = root.find(_tag("envelope"))
    ag_el = envelope_el.find(_tag("aboveGroundWalls")).find(_tag("agWall"))
    wins_el = ag_el.find(_tag("windows"))
    assert wins_el is not None
    win_el = wins_el.find(_tag("window"))
    assert win_el is not None
    assert win_el.find(_tag("glazingType")).text == "DOUBLE"
    assert float(win_el.find(_tag("propUvalue")).text) == pytest.approx(0.28, rel=1e-3)


def test_write_rxl_roof():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    envelope_el = root.find(_tag("envelope"))
    roofs_el = envelope_el.find(_tag("roofs"))
    assert roofs_el is not None
    roof_el = roofs_el.find(_tag("roof"))
    assert roof_el is not None
    assert roof_el.find(_tag("roofType")).text == "WOOD_CATHEDRAL"


def test_write_rxl_floor():
    env = _make_simple_envelope()
    result = write_rxl(env, _METADATA, 0.5)
    root = ET.fromstring(result)
    envelope_el = root.find(_tag("envelope"))
    floors_el = envelope_el.find(_tag("floors"))
    assert floors_el is not None
    floor_el = floors_el.find(_tag("floor"))
    assert floor_el is not None
    assert floor_el.find(_tag("floorType")).text == "ALL_WOOD_JOIST_TRUSS_FLOOR"


def test_write_rxl_below_grade_wall():
    bg_wall = WallData(
        gross_area_ft2=200.0,
        u_value=0.08,
        cavity_r=0.0,
        continuous_r=10.0,
        orientation="BACK",
        is_below_grade=True,
        wall_height_ft=8.0,
        below_grade_height_ft=4.0,
    )
    env = EnvelopeData(
        walls=[bg_wall],
        roofs=[],
        floors=[],
        conditioned_floor_area_ft2=500.0,
    )
    result = write_rxl(env, _METADATA, 0.4)
    root = ET.fromstring(result)
    envelope_el = root.find(_tag("envelope"))
    bgs_el = envelope_el.find(_tag("belowGroundWalls"))
    assert bgs_el is not None
    bg_el = bgs_el.find(_tag("bgWall"))
    assert bg_el is not None
    assert bg_el.find(_tag("wallHeightBelowGrade")) is not None
    assert float(bg_el.find(_tag("wallHeightBelowGrade")).text) == pytest.approx(4.0)


def test_write_rxl_empty_metadata():
    env = _make_simple_envelope()
    result = write_rxl(env, {}, 0.5)
    # Should not crash and should produce valid XML
    root = ET.fromstring(result)
    assert root.tag == _tag("building")


def test_write_rxl_special_chars_in_title():
    meta = dict(_METADATA)
    meta["project"] = dict(_METADATA["project"])
    meta["project"]["title"] = "Smith & Jones <House>"
    env = _make_simple_envelope()
    # Should produce valid XML (title is in CDATA)
    result = write_rxl(env, meta, 0.5)
    root = ET.fromstring(result)
    assert root is not None
