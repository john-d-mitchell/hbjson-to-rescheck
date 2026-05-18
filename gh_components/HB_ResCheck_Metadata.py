"""HB ResCheck Metadata
Attach ResCheck project metadata to a Honeybee Model for export.
-
Args:
    _model: A Honeybee Model object.
    _project_title: Project title string.
    _address: Street address.
    _city: City name.
    _state: State abbreviation (e.g. NY).
    _zip: ZIP code.
    _owner_name: Owner or firm name.
    _location_state: Full state name for ResCheck climate lookup (e.g. "New York").
    _location_city: City + county string for ResCheck climate lookup (e.g. "Woodstock (Ulster)").
    _front_door_faces: Cardinal direction the front door faces (N, S, E, W, NE, NW, SE, SW).
    _construction_type: SINGLE_FAMILY, MULTIFAMILY, etc. Default: SINGLE_FAMILY.
    _project_type: NEW_CONSTRUCTION or ADDITION. Default: NEW_CONSTRUCTION.
    _iecc_code: IECC code string e.g. IECC2024. Default: IECC2021.
    _compliance_mode: UA or PRESCRIPTIVE. Default: UA.
    _duct_location: CONDITIONED_SPACE_ONLY, etc. Default: CONDITIONED_SPACE_ONLY.
    _all_electric: Boolean. Default: False.
    _has_heat_pump: Boolean. Default: False.
Returns:
    model: The Honeybee Model with ResCheck metadata attached.
"""
import scriptcontext  # noqa

if _model is not None:
    model = _model.duplicate()

    if model.user_data is None:
        model.user_data = {}

    model.user_data['rescheck'] = {
        'project': {
            'title': _project_title or '',
            'address': _address or '',
            'city': _city or '',
            'state': _state or '',
            'zip': _zip or '',
        },
        'owner': {
            'name': _owner_name or '',
        },
        'location': {
            'state': _location_state or '',
            'city': _location_city or '',
        },
        'building': {
            'front_door_faces': _front_door_faces or 'S',
            'construction_type': _construction_type or 'SINGLE_FAMILY',
            'project_type': _project_type or 'NEW_CONSTRUCTION',
            'iecc_code': _iecc_code or 'IECC2021',
            'compliance_mode': _compliance_mode or 'UA',
            'duct_location': _duct_location or 'CONDITIONED_SPACE_ONLY',
            'all_electric': bool(_all_electric),
            'has_heat_pump': bool(_has_heat_pump),
        }
    }
else:
    model = None
