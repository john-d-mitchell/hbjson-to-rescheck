# hbjson-to-rescheck

Convert a Honeybee Model (`.hbjson`) to a ResCheck `.rxl` file for IECC energy code compliance reporting.

## What it does

ResCheck is the free DOE/PNNL tool used to demonstrate compliance with the IECC residential energy code. This converter bridges Honeybee/EnergyPlus energy models (the de-facto standard for passive-house and high-performance residential design) to ResCheck's XML format, eliminating manual data re-entry.

## Architecture

The converter has two parts:

### 1. Grasshopper Component (`gh_components/HB_ResCheck_Metadata.py`)

A GHPython component that attaches ResCheck project metadata (project title, address, climate location, IECC version, etc.) to a Honeybee Model object. The component stores metadata in the model's `user_data` dict under the key `rescheck`, which persists through `.hbjson` serialization.

**Inputs:**

| Parameter | Description |
|---|---|
| `_model` | Honeybee Model object |
| `_project_title` | Project title |
| `_address` | Street address |
| `_city` / `_state` / `_zip` | Project address fields |
| `_owner_name` | Owner or firm name |
| `_location_state` | Full state name for ResCheck climate lookup (e.g. `"New York"`) |
| `_location_city` | City + county for climate lookup (e.g. `"Woodstock (Ulster)"`) |
| `_front_door_faces` | Cardinal direction the front door faces: `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW` |
| `_construction_type` | `SINGLE_FAMILY`, `MULTIFAMILY`, etc. |
| `_project_type` | `NEW_CONSTRUCTION` or `ADDITION` |
| `_iecc_code` | e.g. `IECC2021`, `IECC2024` |
| `_compliance_mode` | `UA` or `PRESCRIPTIVE` |
| `_duct_location` | e.g. `CONDITIONED_SPACE_ONLY` |
| `_all_electric` | Boolean |
| `_has_heat_pump` | Boolean |

**Output:** `model` — the Model with metadata attached, ready to serialize with `HB Model To File`.

### 2. CLI Converter (`hbjson_to_rxl.py`)

```
python hbjson_to_rxl.py model.hbjson output.rxl
```

Reads the `.hbjson`, extracts the envelope geometry and construction assemblies, converts to imperial units, maps to ResCheck orientation conventions, and writes a valid `.rxl` XML file.

## Usage

```bash
python hbjson_to_rxl.py path/to/model.hbjson path/to/output.rxl
```

Then open the `.rxl` in ResCheck Desktop or submit via the ResCheck web tool.

## Metadata schema

The `rescheck` metadata dict (stored in `user_data.rescheck` by the GH component, or `properties.rescheck` for direct embedding) has the following structure:

```json
{
  "project": {
    "title": "Smith Residence",
    "address": "123 Main St",
    "city": "Woodstock",
    "state": "NY",
    "zip": "12498"
  },
  "owner": {
    "name": "Jane Smith"
  },
  "location": {
    "state": "New York",
    "city": "Woodstock (Ulster)"
  },
  "building": {
    "front_door_faces": "S",
    "construction_type": "SINGLE_FAMILY",
    "project_type": "NEW_CONSTRUCTION",
    "iecc_code": "IECC2021",
    "compliance_mode": "UA",
    "duct_location": "CONDITIONED_SPACE_ONLY",
    "all_electric": true,
    "has_heat_pump": true
  }
}
```

## Module overview

| Module | Responsibility |
|---|---|
| `rescheck/units.py` | SI → IP unit conversion (m² → ft², m → ft) |
| `rescheck/infiltration.py` | ACH50 → natural ACH (÷20 rule) |
| `rescheck/assembly.py` | Cavity / continuous R-value split from EnergyMaterial layers |
| `rescheck/envelope.py` | Face extraction, orientation mapping, sub-face handling |
| `rescheck/writer.py` | XML serialization to ResCheck RXL schema |

## Dependencies

Standard library only — no pip install required for the converter (`json`, `math`, `html`, `xml.etree.ElementTree`).

Tests require `pytest`:
```bash
pip install pytest
python -m pytest tests/ -v
```

## Orientation convention

Face orientation is derived from the face normal vector relative to the `front_door_faces` direction:

| Relative angle | ResCheck label |
|---|---|
| 315°–45° | `FRONT` |
| 45°–135° | `RIGHT_SIDE` |
| 135°–225° | `BACK` |
| 225°–315° | `LEFT_SIDE` |

Note: "right" and "left" are from the perspective of someone standing **inside** the building looking toward the front.

## Infiltration

ACH50 is read from `properties.ph.infiltration_ach50` (honeybee-ph convention) or from the first room's PH properties. It is converted to natural ACH using the residential ÷20 rule of thumb.

If no ACH50 is found in the model, a default of 0.5 ACH natural is used.
