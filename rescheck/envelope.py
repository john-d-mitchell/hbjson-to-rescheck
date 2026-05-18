"""Envelope extraction from hbjson.

Reads a honeybee Model dict and returns structured EnvelopeData containing
walls, roofs, floors, windows, and doors in imperial units with ResCheck
orientation labels.
"""

import math
from dataclasses import dataclass, field

from rescheck.units import m2_to_ft2, m_to_ft
from rescheck.assembly import classify_layers, assembly_u_value


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WindowData:
    area_ft2: float
    u_value: float
    shgc: float
    orientation: str  # FRONT | BACK | LEFT_SIDE | RIGHT_SIDE
    height_ft: float = 0.0


@dataclass
class DoorData:
    area_ft2: float
    u_value: float
    orientation: str


@dataclass
class WallData:
    gross_area_ft2: float
    u_value: float
    cavity_r: float
    continuous_r: float
    orientation: str
    is_below_grade: bool
    wall_height_ft: float = 0.0
    below_grade_height_ft: float = 0.0
    windows: list = field(default_factory=list)
    doors: list = field(default_factory=list)


@dataclass
class RoofData:
    gross_area_ft2: float
    u_value: float
    cavity_r: float
    continuous_r: float
    roof_type: str  # WOOD_CATHEDRAL | WOOD_FRAME_ATTIC


@dataclass
class FloorData:
    gross_area_ft2: float
    cavity_r: float
    floor_type: str  # ALL_WOOD_JOIST_TRUSS_FLOOR | SLAB_FLOOR


@dataclass
class EnvelopeData:
    walls: list
    roofs: list
    floors: list
    conditioned_floor_area_ft2: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CARDINAL_BEARINGS = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
}


def _face_bearing(normal: list) -> float:
    """Compute bearing angle of a face normal projected onto the XY plane.

    0 = North, 90 = East, 180 = South, 270 = West.
    """
    nx, ny = normal[0], normal[1]
    angle_rad = math.atan2(nx, ny)
    angle_deg = math.degrees(angle_rad)
    return angle_deg % 360.0


def _orientation_label(face_normal: list, front_bearing: float) -> str:
    """Return ResCheck orientation label relative to front-door direction."""
    bearing = _face_bearing(face_normal)
    relative = (bearing - front_bearing + 360.0) % 360.0

    if relative < 45.0 or relative >= 315.0:
        return "FRONT"
    elif relative < 135.0:
        return "RIGHT_SIDE"
    elif relative < 225.0:
        return "BACK"
    else:
        return "LEFT_SIDE"


def _polygon_area_m2(vertices: list) -> float:
    """Compute 3D polygon area using the cross-product (shoelace) method.

    Args:
        vertices: List of [x, y, z] coordinate lists (floats).

    Returns:
        Area in m².
    """
    n = len(vertices)
    if n < 3:
        return 0.0
    # Newell's method for polygon normal and area
    cross = [0.0, 0.0, 0.0]
    for i in range(n):
        v0 = vertices[i]
        v1 = vertices[(i + 1) % n]
        cross[0] += (v0[1] - v1[1]) * (v0[2] + v1[2])
        cross[1] += (v0[2] - v1[2]) * (v0[0] + v1[0])
        cross[2] += (v0[0] - v1[0]) * (v0[1] + v1[1])
    return 0.5 * math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)


def _face_normal(vertices: list) -> list:
    """Return the unit normal of a polygon from its vertices."""
    if len(vertices) < 3:
        return [0.0, 0.0, 1.0]
    v0 = vertices[0]
    v1 = vertices[1]
    v2 = vertices[2]
    e1 = [v1[i] - v0[i] for i in range(3)]
    e2 = [v2[i] - v0[i] for i in range(3)]
    cross = [
        e1[1] * e2[2] - e1[2] * e2[1],
        e1[2] * e2[0] - e1[0] * e2[2],
        e1[0] * e2[1] - e1[1] * e2[0],
    ]
    mag = math.sqrt(sum(c ** 2 for c in cross))
    if mag == 0.0:
        return [0.0, 0.0, 1.0]
    return [c / mag for c in cross]


def _vertices_from_face(face: dict) -> list:
    """Extract flat vertex list from a face geometry dict."""
    geom = face.get("geometry", {})
    return geom.get("vertices", [])


def _wall_heights(vertices: list):
    """Return (total_height_ft, below_grade_height_ft) from face vertices."""
    if not vertices:
        return 0.0, 0.0
    z_vals = [v[2] for v in vertices]
    z_min = min(z_vals)
    z_max = max(z_vals)
    total_m = z_max - z_min
    below_grade_m = max(0.0, -z_min)  # portion below z=0
    return m_to_ft(total_m), m_to_ft(below_grade_m)


def _build_construction_index(hbjson: dict) -> dict:
    """Build identifier → construction dict mapping from model-level constructions."""
    index = {}
    props = hbjson.get("properties", {})
    energy = props.get("energy", {})
    for constr in energy.get("constructions", []):
        ident = constr.get("identifier", "")
        if ident:
            index[ident] = constr
    return index


def _get_layers(construction: dict, constr_index: dict) -> list:
    """Return the layer dicts for a construction.

    Handles both opaque constructions (list of material identifiers in
    ``layers``) and simple constructions. The materials themselves must be
    looked up separately; here we return a list of dicts with at least
    ``identifier`` and ``r_value``.
    """
    # Some constructions embed full material objects directly in ``layers``
    layers_raw = construction.get("layers", [])
    if not layers_raw:
        return []

    # If layers contain dicts (embedded material objects), use them directly
    if isinstance(layers_raw[0], dict):
        return layers_raw

    # Otherwise layers is a list of identifier strings; look up in materials index
    materials_index = construction.get("_materials_index", {})
    result = []
    for layer_id in layers_raw:
        if isinstance(layer_id, dict):
            result.append(layer_id)
        elif layer_id in materials_index:
            result.append(materials_index[layer_id])
        else:
            # Return a stub so we don't crash
            result.append({"identifier": layer_id, "r_value": 0.0})
    return result


def _build_materials_index(hbjson: dict) -> dict:
    """Build identifier → material dict from model-level materials."""
    index = {}
    props = hbjson.get("properties", {})
    energy = props.get("energy", {})
    for mat in energy.get("materials", []):
        ident = mat.get("identifier", "")
        if ident:
            index[ident] = mat
    return index


def _resolve_layers(construction: dict, mat_index: dict) -> list:
    """Return resolved layer dicts for a construction."""
    layers_raw = construction.get("layers", [])
    if not layers_raw:
        return []

    if isinstance(layers_raw[0], dict):
        return layers_raw

    result = []
    for layer_id in layers_raw:
        if isinstance(layer_id, dict):
            result.append(layer_id)
        elif layer_id in mat_index:
            result.append(mat_index[layer_id])
        else:
            result.append({"identifier": str(layer_id), "r_value": 0.0})
    return result


def _aperture_u_shgc(aperture: dict, constr_index: dict, mat_index: dict):
    """Return (u_value, shgc) for a window/door aperture in imperial."""
    # Try energy properties on aperture directly
    energy = aperture.get("properties", {}).get("energy", {})
    constr_id = energy.get("construction")
    if constr_id and constr_id in constr_index:
        constr = constr_index[constr_id]
        # Window constructions have u_factor and shgc directly
        u_si = constr.get("u_factor") or constr.get("u_value") or 0.0
        shgc = constr.get("shgc", 0.0)
        # Convert U from SI (W/m²K) to IP (BTU/h·ft²·°F): multiply by 0.17611
        u_ip = u_si * 0.17611
        return u_ip, shgc

    # Fallback: try u_factor/shgc directly on aperture properties
    u_si = energy.get("u_factor") or energy.get("u_value") or 0.0
    shgc = energy.get("shgc", 0.0)
    u_ip = u_si * 0.17611
    return u_ip, shgc


def _opaque_assembly(face: dict, constr_index: dict, mat_index: dict):
    """Return (cavity_r, continuous_r, u_value) for an opaque face."""
    energy = face.get("properties", {}).get("energy", {})
    constr_id = energy.get("construction")
    if constr_id and constr_id in constr_index:
        constr = constr_index[constr_id]
        layers = _resolve_layers(constr, mat_index)
        cavity_r, continuous_r = classify_layers(layers)
        u_val = assembly_u_value(layers)
        return cavity_r, continuous_r, u_val
    return 0.0, 0.0, 0.0


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_envelope(hbjson: dict, front_door_faces: str = "S") -> EnvelopeData:
    """Extract envelope data from an hbjson model dict.

    Args:
        hbjson: Parsed honeybee Model JSON dict.
        front_door_faces: Cardinal direction the front door faces
            (N, NE, E, SE, S, SW, W, NW).

    Returns:
        EnvelopeData with walls, roofs, floors, and conditioned floor area.
    """
    front_bearing = float(_CARDINAL_BEARINGS.get(front_door_faces.upper(), 180))
    constr_index = _build_construction_index(hbjson)
    mat_index = _build_materials_index(hbjson)

    walls = []
    roofs = []
    floors = []
    conditioned_area_m2 = 0.0

    rooms = hbjson.get("rooms", [])

    for room in rooms:
        for face in room.get("faces", []):
            face_type = face.get("face_type", "")
            bc = face.get("boundary_condition", "")

            # Boundary condition can be a string like "Outdoors" / "Ground"
            # or a dict like {"boundary_condition_objects": [...]} for adjacent faces
            is_outdoors = bc == "Outdoors"
            is_ground = bc == "Ground"
            is_interior = isinstance(bc, dict) or (
                isinstance(bc, str) and bc not in ("Outdoors", "Ground")
            )

            vertices = _vertices_from_face(face)
            area_m2 = _polygon_area_m2(vertices)

            if face_type == "Floor":
                if not is_interior:
                    conditioned_area_m2 += area_m2

                if is_outdoors:
                    cavity_r, continuous_r, _ = _opaque_assembly(face, constr_index, mat_index)
                    floors.append(FloorData(
                        gross_area_ft2=m2_to_ft2(area_m2),
                        cavity_r=cavity_r,
                        floor_type="ALL_WOOD_JOIST_TRUSS_FLOOR",
                    ))
                elif is_ground:
                    # Slab — out of scope per spec; skip
                    pass
                # else interior floor — skip

            elif face_type == "RoofCeiling" and is_outdoors:
                cavity_r, continuous_r, u_val = _opaque_assembly(face, constr_index, mat_index)
                roofs.append(RoofData(
                    gross_area_ft2=m2_to_ft2(area_m2),
                    u_value=u_val,
                    cavity_r=cavity_r,
                    continuous_r=continuous_r,
                    roof_type="WOOD_CATHEDRAL",
                ))

            elif face_type == "Wall":
                # Determine face normal from geometry
                if vertices:
                    normal = _face_normal(vertices)
                else:
                    normal = face.get("geometry", {}).get("normal", [0.0, 1.0, 0.0])

                orientation = _orientation_label(normal, front_bearing)
                cavity_r, continuous_r, u_val = _opaque_assembly(face, constr_index, mat_index)
                total_height_ft, below_grade_ft = _wall_heights(vertices)

                is_below = is_ground

                wall = WallData(
                    gross_area_ft2=m2_to_ft2(area_m2),
                    u_value=u_val,
                    cavity_r=cavity_r,
                    continuous_r=continuous_r,
                    orientation=orientation,
                    is_below_grade=is_below,
                    wall_height_ft=total_height_ft,
                    below_grade_height_ft=below_grade_ft,
                )

                # Sub-faces: apertures (windows) and doors
                for aperture in face.get("apertures", []):
                    ap_verts = _vertices_from_face(aperture)
                    if not ap_verts:
                        ap_verts = aperture.get("geometry", {}).get("vertices", [])
                    ap_area_m2 = _polygon_area_m2(ap_verts)
                    u_ip, shgc = _aperture_u_shgc(aperture, constr_index, mat_index)
                    ap_h_ft = 0.0
                    if ap_verts:
                        z_vals = [v[2] for v in ap_verts]
                        ap_h_ft = m_to_ft(max(z_vals) - min(z_vals))
                    wall.windows.append(WindowData(
                        area_ft2=m2_to_ft2(ap_area_m2),
                        u_value=u_ip,
                        shgc=shgc,
                        orientation=orientation,
                        height_ft=ap_h_ft,
                    ))

                for door in face.get("doors", []):
                    door_verts = _vertices_from_face(door)
                    if not door_verts:
                        door_verts = door.get("geometry", {}).get("vertices", [])
                    door_area_m2 = _polygon_area_m2(door_verts)
                    u_ip, _ = _aperture_u_shgc(door, constr_index, mat_index)
                    wall.doors.append(DoorData(
                        area_ft2=m2_to_ft2(door_area_m2),
                        u_value=u_ip,
                        orientation=orientation,
                    ))

                walls.append(wall)

    return EnvelopeData(
        walls=walls,
        roofs=roofs,
        floors=floors,
        conditioned_floor_area_ft2=m2_to_ft2(conditioned_area_m2),
    )
