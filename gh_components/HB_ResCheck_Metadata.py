"""HB ResCheck Metadata
Attach ResCheck project metadata to a Honeybee Model for export.
-
SETUP: Right-click this component and add the following inputs.
Prefix required inputs with underscore. Optional inputs can use any name.

Required input parameters (add via right-click > Manage Attributes > Inputs):
  _model            : Honeybee Model object (connect from your HB canvas)

Optional input parameters:
  _project_title    : str  - e.g. "My House"
  _address          : str  - street address
  _city             : str  - project city
  _state            : str  - state abbreviation e.g. "NY"
  _zip              : str  - ZIP code
  _owner_name       : str  - owner or firm name
  _location_state   : str  - full state name for ResCheck e.g. "New York"
  _location_city    : str  - city + county e.g. "Woodstock (Ulster)"
  _front_door_faces : str  - N, S, E, W, NE, NW, SE, SW (default: S)
  _construction_type: str  - SINGLE_FAMILY (default)
  _project_type     : str  - NEW_CONSTRUCTION (default)
  _iecc_code        : str  - e.g. IECC2024 (default: IECC2021)
  _compliance_mode  : str  - UA (default) or PRESCRIPTIVE
  _duct_location    : str  - CONDITIONED_SPACE_ONLY (default)
  _all_electric     : bool - True/False (default: False)
  _has_heat_pump    : bool - True/False (default: False)

Output parameter:
  model             : Honeybee Model with ResCheck metadata in user_data
-
Args:
    _model: Honeybee Model object.
Returns:
    model: Model with ResCheck metadata attached to user_data['rescheck'].
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
# Unwrap GH_ObjectWrapper if needed (GHPython sometimes wraps objects)
if hasattr(_m, 'Value'):
    _m = _m.Value
if _m is not None:
    model = _m.duplicate()

    if model.user_data is None:
        model.user_data = {}

    model.user_data['rescheck'] = {
        'project': {
            'title': _get('_project_title', ''),
            'address': _get('_address', ''),
            'city': _get('_city', ''),
            'state': _get('_state', ''),
            'zip': _get('_zip', ''),
        },
        'owner': {
            'name': _get('_owner_name', ''),
        },
        'location': {
            'state': _get('_location_state', ''),
            'city': _get('_location_city', ''),
        },
        'building': {
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
