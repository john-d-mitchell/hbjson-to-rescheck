"""HB ResCheck Metadata
Attaches ResCheck-specific metadata to a Honeybee-PH Model.
Reads project/owner data from the existing HBPH project team (set via the
'HBPH - Set Model Project Data' component upstream). Only the fields that
are NOT available in the PH team data are collected here.
-
Connect this component downstream of 'HBPH - Set Model Project Data'.
-
SETUP: Add the following input parameters to this component
(right-click > Manage Attributes > Inputs):

  _model             : HB Model (connect from HBPH Set Model Project Data output)
  _state             : str  - state abbreviation e.g. "NY" (not stored in PH team)
  _location_state    : str  - full state name for ResCheck climate e.g. "New York"
  _location_city     : str  - city + county for ResCheck climate e.g. "Woodstock (Ulster)"
  _front_door_faces  : str  - cardinal direction front door faces: N S E W NE NW SE SW
  _construction_type : str  - SINGLE_FAMILY (default)
  _project_type      : str  - NEW_CONSTRUCTION (default) or ADDITION
  _iecc_code         : str  - e.g. IECC2024 (default: IECC2021)
  _compliance_mode   : str  - UA (default) or PRESCRIPTIVE
  _duct_location     : str  - CONDITIONED_SPACE_ONLY (default)
  _all_electric      : bool - default: False
  _has_heat_pump     : bool - default: False

Output parameter:
  model              : HB Model with ResCheck metadata in user_data['rescheck']
-
Args:
    _model: HB Model from upstream HBPH Set Model Project Data component.
Returns:
    model: Model with ResCheck metadata attached.
"""


def _get(name, default=None):
    """Safely read a GHPython input variable that may not be wired yet."""
    try:
        val = globals()[name]
        return val if val is not None else default
    except KeyError:
        return default


model = None

_m = _get('_model')
if hasattr(_m, 'Value'):
    _m = _m.Value

if _m is not None:
    model = type(_m).from_dict(_m.to_dict())

    if model.user_data is None:
        model.user_data = {}

    model.user_data['rescheck'] = {
        'location': {
            'state': _get('_location_state', ''),
            'city': _get('_location_city', ''),
        },
        'building': {
            'state': _get('_state', ''),
            'front_door_faces': _get('_front_door_faces', 'S'),
            'construction_type': _get('_construction_type', 'SINGLE_FAMILY'),
            'project_type': _get('_project_type', 'NEW_CONSTRUCTION'),
            'iecc_code': _get('_iecc_code', 'IECC2021'),
            'compliance_mode': _get('_compliance_mode', 'UA'),
            'duct_location': _get('_duct_location', 'CONDITIONED_SPACE_ONLY'),
            'all_electric': bool(_get('_all_electric', False)),
            'has_heat_pump': bool(_get('_has_heat_pump', False)),
        }
    }
