"""Tests for rescheck.envelope.

Uses a minimal valid hbjson dict representing a single shoebox room:
- 4 above-grade walls (N, S, E, W)
- 1 roof
- 1 floor (ground)
- 1 window on the south wall

Front door faces South, so:
  FRONT = south wall (normal ≈ [0, -1, 0], bearing 180°)
  BACK  = north wall (normal ≈ [0,  1, 0], bearing 0°)
  RIGHT_SIDE = east wall
  LEFT_SIDE  = west wall
"""
import math
import pytest

from rescheck.envelope import (
    extract_envelope,
    _polygon_area_m2,
    _face_bearing,
    _orientation_label,
)


# ---------------------------------------------------------------------------
# Helpers to build minimal hbjson geometry
# ---------------------------------------------------------------------------

def _rect_face_vertices(x0, y0, z0, x1, y1, z1):
    """Return 4 vertices of an axis-aligned rectangular face."""
    # All four corners in counter-clockwise order (from outside)
    return [
        [x0, y0, z0],
        [x1, y0, z0],
        [x1, y1, z1],
        [x0, y1, z1],
    ]


def _make_face(face_type, bc, vertices, normal, construction_id=None,
               apertures=None, doors=None):
    face = {
        "face_type": face_type,
        "boundary_condition": bc,
        "geometry": {
            "vertices": vertices,
            "normal": normal,
        },
        "properties": {
            "energy": {},
        },
        "apertures": apertures or [],
        "doors": doors or [],
    }
    if construction_id:
        face["properties"]["energy"]["construction"] = construction_id
    return face


def _make_aperture(vertices, construction_id=None):
    ap = {
        "geometry": {"vertices": vertices},
        "properties": {
            "energy": {},
        },
    }
    if construction_id:
        ap["properties"]["energy"]["construction"] = construction_id
    return ap


# ---------------------------------------------------------------------------
# Minimal hbjson shoebox
# ---------------------------------------------------------------------------

# Room: 10m × 10m × 3m, origin at (0, 0, 0)

_R21_SI = 21.0 / 5.678   # R-21 batt in SI
_XPS5_SI = 5.0 / 5.678   # R-5 XPS in SI
_WINDOW_U_SI = 1.0        # ~0.176 IP

_WALL_CONSTRUCTION = {
    "identifier": "WallConstruction",
    "layers": [
        {"identifier": "Fiberglass_Batt_R21", "r_value": _R21_SI},
        {"identifier": "OSB_Sheath", "r_value": 0.10},
    ],
}

_ROOF_CONSTRUCTION = {
    "identifier": "RoofConstruction",
    "layers": [
        {"identifier": "Cellulose_R38", "r_value": 38.0 / 5.678},
    ],
}

_WINDOW_CONSTRUCTION = {
    "identifier": "WindowConstruction",
    "u_factor": _WINDOW_U_SI,
    "shgc": 0.40,
}

# South wall: y=0, normal [0, -1, 0] — will be FRONT when front_door_faces="S"
_SOUTH_WALL_VERTS = [
    [0, 0, 0], [10, 0, 0], [10, 0, 3], [0, 0, 3]
]
# Small south window
_SOUTH_WIN_VERTS = [
    [2, 0, 1], [4, 0, 1], [4, 0, 2.5], [2, 0, 2.5]
]

_NORTH_WALL_VERTS = [
    [10, 10, 0], [0, 10, 0], [0, 10, 3], [10, 10, 3]
]
_EAST_WALL_VERTS = [
    [10, 0, 0], [10, 10, 0], [10, 10, 3], [10, 0, 3]
]
_WEST_WALL_VERTS = [
    [0, 10, 0], [0, 0, 0], [0, 0, 3], [0, 10, 3]
]
_ROOF_VERTS = [
    [0, 0, 3], [10, 0, 3], [10, 10, 3], [0, 10, 3]
]
_FLOOR_VERTS = [
    [0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]
]

_SOUTH_WIN = _make_aperture(_SOUTH_WIN_VERTS, "WindowConstruction")

_SHOEBOX_ROOM = {
    "faces": [
        _make_face("Wall", "Outdoors", _SOUTH_WALL_VERTS, [0, -1, 0],
                   "WallConstruction", apertures=[_SOUTH_WIN]),
        _make_face("Wall", "Outdoors", _NORTH_WALL_VERTS, [0, 1, 0],
                   "WallConstruction"),
        _make_face("Wall", "Outdoors", _EAST_WALL_VERTS, [1, 0, 0],
                   "WallConstruction"),
        _make_face("Wall", "Outdoors", _WEST_WALL_VERTS, [-1, 0, 0],
                   "WallConstruction"),
        _make_face("RoofCeiling", "Outdoors", _ROOF_VERTS, [0, 0, 1],
                   "RoofConstruction"),
        _make_face("Floor", "Ground", _FLOOR_VERTS, [0, 0, -1]),
    ]
}

_SHOEBOX_HBJSON = {
    "rooms": [_SHOEBOX_ROOM],
    "properties": {
        "energy": {
            "constructions": [
                _WALL_CONSTRUCTION,
                _ROOF_CONSTRUCTION,
                _WINDOW_CONSTRUCTION,
            ],
            "materials": [],
        }
    }
}


# ---------------------------------------------------------------------------
# Tests: low-level helpers
# ---------------------------------------------------------------------------

def test_polygon_area_unit_square():
    verts = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
    assert _polygon_area_m2(verts) == pytest.approx(1.0)


def test_polygon_area_rectangle():
    verts = [[0, 0, 0], [10, 0, 0], [10, 5, 0], [0, 5, 0]]
    assert _polygon_area_m2(verts) == pytest.approx(50.0)


def test_polygon_area_vertical_wall():
    # 10m × 3m vertical wall
    assert _polygon_area_m2(_SOUTH_WALL_VERTS) == pytest.approx(30.0)


def test_polygon_area_too_few_vertices():
    assert _polygon_area_m2([[0, 0, 0], [1, 0, 0]]) == 0.0


def test_face_bearing_north():
    # Normal [0, 1, 0] → north-facing → bearing 0
    assert _face_bearing([0, 1, 0]) == pytest.approx(0.0)


def test_face_bearing_south():
    assert _face_bearing([0, -1, 0]) == pytest.approx(180.0)


def test_face_bearing_east():
    assert _face_bearing([1, 0, 0]) == pytest.approx(90.0)


def test_face_bearing_west():
    assert _face_bearing([-1, 0, 0]) == pytest.approx(270.0)


def test_orientation_label_front():
    # South-facing wall, front = south → FRONT
    assert _orientation_label([0, -1, 0], 180.0) == "FRONT"


def test_orientation_label_back():
    # North-facing wall, front = south → BACK
    assert _orientation_label([0, 1, 0], 180.0) == "BACK"


def test_orientation_label_right_side():
    # West-facing wall, front = south → RIGHT_SIDE
    # (standing inside facing south, west is to your right)
    assert _orientation_label([-1, 0, 0], 180.0) == "RIGHT_SIDE"


def test_orientation_label_left_side():
    # East-facing wall, front = south → LEFT_SIDE
    # (standing inside facing south, east is to your left)
    assert _orientation_label([1, 0, 0], 180.0) == "LEFT_SIDE"


# ---------------------------------------------------------------------------
# Tests: extract_envelope
# ---------------------------------------------------------------------------

def test_extract_envelope_wall_count():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    assert len(env.walls) == 4


def test_extract_envelope_roof_count():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    assert len(env.roofs) == 1


def test_extract_envelope_no_exposed_floors():
    # Ground floor → slab, skipped; no exposed floor faces
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    assert len(env.floors) == 0


def test_extract_envelope_conditioned_floor_area():
    # 10m × 10m = 100 m² → 1076.39 ft²
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    assert env.conditioned_floor_area_ft2 == pytest.approx(100.0 * 10.7639, rel=1e-3)


def test_extract_envelope_south_wall_is_front():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    south_walls = [w for w in env.walls if w.orientation == "FRONT"]
    assert len(south_walls) == 1


def test_extract_envelope_north_wall_is_back():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    north_walls = [w for w in env.walls if w.orientation == "BACK"]
    assert len(north_walls) == 1


def test_extract_envelope_south_wall_has_window():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    south_wall = next(w for w in env.walls if w.orientation == "FRONT")
    assert len(south_wall.windows) == 1


def test_extract_envelope_window_area():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    south_wall = next(w for w in env.walls if w.orientation == "FRONT")
    win = south_wall.windows[0]
    # Window: 2m wide × 1.5m tall = 3 m²
    assert win.area_ft2 == pytest.approx(3.0 * 10.7639, rel=1e-3)


def test_extract_envelope_wall_areas():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    # Each wall: 10m × 3m = 30 m² → 322.917 ft²
    for wall in env.walls:
        assert wall.gross_area_ft2 == pytest.approx(30.0 * 10.7639, rel=1e-3)


def test_extract_envelope_cavity_r_from_construction():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    for wall in env.walls:
        # R-21 cavity only; OSB is structural
        assert wall.cavity_r == pytest.approx(21.0, rel=1e-2)
        assert wall.continuous_r == pytest.approx(0.0)


def test_extract_envelope_roof_type_cathedral():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    assert env.roofs[0].roof_type == "WOOD_CATHEDRAL"


def test_extract_envelope_walls_not_below_grade():
    env = extract_envelope(_SHOEBOX_HBJSON, "S")
    for wall in env.walls:
        assert not wall.is_below_grade


def test_extract_envelope_front_door_north():
    # When front = N, north wall (normal [0,1,0]) → FRONT
    env = extract_envelope(_SHOEBOX_HBJSON, "N")
    north_walls = [w for w in env.walls if w.orientation == "FRONT"]
    assert len(north_walls) == 1


# ---------------------------------------------------------------------------
# Consolidation tests
# ---------------------------------------------------------------------------

def test_wall_consolidation_same_assembly_orientation():
    # Two south-facing walls with the same construction → merged into one entry.
    wall_a = _make_face("Wall", "Outdoors", _SOUTH_WALL_VERTS, [0, -1, 0], "WallConstruction")
    wall_b = _make_face("Wall", "Outdoors",
                        [[0, 0, 0], [5, 0, 0], [5, 0, 3], [0, 0, 3]],  # 5m × 3m
                        [0, -1, 0], "WallConstruction")
    hbjson = {
        "rooms": [{"faces": [wall_a, wall_b]}],
        "properties": {"energy": {"constructions": [_WALL_CONSTRUCTION], "materials": []}},
    }
    env = extract_envelope(hbjson, "S")
    assert len(env.walls) == 1
    # Combined area: (10*3 + 5*3) m² = 45 m²
    assert env.walls[0].gross_area_ft2 == pytest.approx(45.0 * 10.7639, rel=1e-3)


def test_wall_consolidation_different_orientations_not_merged():
    # South and north walls with the same construction → two separate entries.
    south = _make_face("Wall", "Outdoors", _SOUTH_WALL_VERTS, [0, -1, 0], "WallConstruction")
    north = _make_face("Wall", "Outdoors", _NORTH_WALL_VERTS, [0, 1, 0], "WallConstruction")
    hbjson = {
        "rooms": [{"faces": [south, north]}],
        "properties": {"energy": {"constructions": [_WALL_CONSTRUCTION], "materials": []}},
    }
    env = extract_envelope(hbjson, "S")
    assert len(env.walls) == 2


def test_wall_consolidation_windows_accumulated():
    # Two south walls each with a window → consolidated wall has both windows.
    win1 = _make_aperture([[1, 0, 0.5], [2, 0, 0.5], [2, 0, 1.5], [1, 0, 1.5]], "WindowConstruction")
    win2 = _make_aperture([[3, 0, 0.5], [4, 0, 0.5], [4, 0, 1.5], [3, 0, 1.5]], "WindowConstruction")
    wall_a = _make_face("Wall", "Outdoors", _SOUTH_WALL_VERTS, [0, -1, 0],
                        "WallConstruction", apertures=[win1])
    wall_b = _make_face("Wall", "Outdoors",
                        [[0, 0, 0], [5, 0, 0], [5, 0, 3], [0, 0, 3]],
                        [0, -1, 0], "WallConstruction", apertures=[win2])
    hbjson = {
        "rooms": [{"faces": [wall_a, wall_b]}],
        "properties": {"energy": {
            "constructions": [_WALL_CONSTRUCTION, _WINDOW_CONSTRUCTION],
            "materials": [],
        }},
    }
    env = extract_envelope(hbjson, "S")
    assert len(env.walls) == 1
    # Both windows share the same construction so they consolidate into one entry
    assert len(env.walls[0].windows) == 1
    assert abs(env.walls[0].windows[0].area_ft2 - 21.528) < 0.1


def test_floor_consolidation_same_assembly():
    floor_a = _make_face("Floor", "Outdoors",
                         [[0, 0, 5], [5, 0, 5], [5, 5, 5], [0, 5, 5]], [0, 0, -1])
    floor_b = _make_face("Floor", "Outdoors",
                         [[5, 0, 5], [10, 0, 5], [10, 5, 5], [5, 5, 5]], [0, 0, -1])
    hbjson = {
        "rooms": [{"faces": [floor_a, floor_b]}],
        "properties": {"energy": {"constructions": [], "materials": []}},
    }
    env = extract_envelope(hbjson, "S")
    assert len(env.floors) == 1
    # Combined area: 25 + 25 = 50 m²
    assert env.floors[0].gross_area_ft2 == pytest.approx(50.0 * 10.7639, rel=1e-3)
