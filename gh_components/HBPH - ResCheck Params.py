# -*- coding: utf-8 -*-
# -*- Python Version: 2.7 -*-
#
# Honeybee-PH: A Plugin for adding Passive-House data to LadybugTools Honeybee-Energy Models
#
# This component is part of the PH-Tools toolkit <https://github.com/PH-Tools>.
#
# Copyright (c) 2024, PH-Tools and bldgtyp, llc <phtools@bldgtyp.com>
# Honeybee-PH is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 3 of the License,
# or (at your option) any later version.
#
# Honeybee-PH is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a copy of the GNU General Public License
# see <https://github.com/PH-Tools/honeybee_ph/blob/main/LICENSE>.
#
# @license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>
#
"""
Attach ResCheck-specific compliance parameters to a Honeybee-PH Model. The
project title, owner, and address are read automatically from the existing PH
Team data set upstream by 'HBPH - Set Model Project Data'. Only the fields
that are not available in the PH Team are collected here.
-
Connect this component downstream of 'HBPH - Set Model Project Data' and
upstream of any ResCheck export workflow.
-
    Args:
        _model: (HB Model) Honeybee model from the upstream 'HBPH - Set Model
            Project Data' component.

        _location_state: (str) Full state name used to select the ResCheck
            climate location. Example: "New York"

        _location_city: (str) City and county string used to select the
            ResCheck climate location. Example: "Woodstock (Ulster)"

        _front_door_faces: (str) Cardinal direction the front door faces.
            Input one of: N  S  E  W  NE  NW  SE  SW
            Default: "S"

        _construction_type: (str) ResCheck construction type.
            Input one of:
                "SINGLE_FAMILY"  (default)
                "MULTIFAMILY"

        _project_type: (str) ResCheck project type.
            Input one of:
                "NEW_CONSTRUCTION"  (default)
                "ADDITION"

        _iecc_code: (str) IECC edition used for compliance.
            Example: "IECC2021"  (default)  |  "IECC2024"

        _compliance_mode: (str) ResCheck compliance pathway.
            Input one of:
                "UA"            (default — U-factor assembly trade-off)
                "PRESCRIPTIVE"

        _duct_location: (str) Primary duct system location.
            Input one of:
                "CONDITIONED_SPACE_ONLY"  (default)
                "UNCONDITIONED_SPACE"

        _all_electric: (bool) True if the building has no combustion equipment.
            Default: True

        _has_heat_pump: (bool) True if a heat pump provides primary heating
            or cooling. Default: True

    Returns:
        model_: (HB Model) The Honeybee model with ResCheck parameters stored
            in model.user_data['rescheck']. Pass this to the ResCheck export
            workflow.
"""

try:
    from typing import Any, Dict, Optional
except ImportError:
    pass  # IronPython 2.7

# ------------------------------------------------------------------------------
import honeybee_ph_rhino._component_info_
reload(honeybee_ph_rhino._component_info_)
ghenv.Component.Name = "HBPH - ResCheck Params"
DEV = honeybee_ph_rhino._component_info_.set_component_params(ghenv, dev='OCT_01_2024')
if DEV:
    pass  # reload local modules here when extracted into honeybee_ph_rhino


# ------------------------------------------------------------------------------
class ResCheckParams(object):
    """ResCheck compliance parameters for a single-family or multifamily building.

    Attributes:
        location_state (str): Full state name for the ResCheck climate selector.
        location_city (str): City + county string for the ResCheck climate selector.
        front_door_faces (str): Cardinal direction the front door faces (N/S/E/W/…).
        construction_type (str): ResCheck construction type identifier.
        project_type (str): ResCheck project type identifier.
        iecc_code (str): IECC edition string (e.g. "IECC2021").
        compliance_mode (str): "UA" or "PRESCRIPTIVE".
        duct_location (str): Primary duct location identifier.
        all_electric (bool): True if no combustion equipment is present.
        has_heat_pump (bool): True if a heat pump is the primary HVAC source.
    """

    def __init__(self):
        # type: () -> None
        self.location_state = ""
        self.location_city = ""
        self.front_door_faces = "S"
        self.construction_type = "SINGLE_FAMILY"
        self.project_type = "NEW_CONSTRUCTION"
        self.iecc_code = "IECC2021"
        self.compliance_mode = "UA"
        self.duct_location = "CONDITIONED_SPACE_ONLY"
        self.all_electric = True
        self.has_heat_pump = True

    def to_dict(self):
        # type: () -> Dict[str, Any]
        return {
            "type": "ResCheckParams",
            "location": {
                "state": self.location_state,
                "city": self.location_city,
            },
            "building": {
                "front_door_faces": self.front_door_faces,
                "construction_type": self.construction_type,
                "project_type": self.project_type,
                "iecc_code": self.iecc_code,
                "compliance_mode": self.compliance_mode,
                "duct_location": self.duct_location,
                "all_electric": self.all_electric,
                "has_heat_pump": self.has_heat_pump,
            },
        }

    @classmethod
    def from_dict(cls, _dict):
        # type: (Dict[str, Any]) -> ResCheckParams
        assert _dict.get("type") == "ResCheckParams", \
            "Expected ResCheckParams. Got {}.".format(_dict.get("type"))
        new_obj = cls()
        loc = _dict.get("location", {})
        new_obj.location_state = loc.get("state", "")
        new_obj.location_city = loc.get("city", "")
        bldg = _dict.get("building", {})
        new_obj.front_door_faces = bldg.get("front_door_faces", "S")
        new_obj.construction_type = bldg.get("construction_type", "SINGLE_FAMILY")
        new_obj.project_type = bldg.get("project_type", "NEW_CONSTRUCTION")
        new_obj.iecc_code = bldg.get("iecc_code", "IECC2021")
        new_obj.compliance_mode = bldg.get("compliance_mode", "UA")
        new_obj.duct_location = bldg.get("duct_location", "CONDITIONED_SPACE_ONLY")
        new_obj.all_electric = bldg.get("all_electric", True)
        new_obj.has_heat_pump = bldg.get("has_heat_pump", True)
        return new_obj

    def __repr__(self):
        return "ResCheckParams: [{} | {} | {}]".format(
            self.iecc_code, self.compliance_mode, self.construction_type
        )

    def ToString(self):
        return self.__repr__()


# ------------------------------------------------------------------------------
model_ = None

if _model:
    _m = _model.Value if hasattr(_model, 'Value') else _model
    model_ = type(_m).from_dict(_m.to_dict())

    params = ResCheckParams()
    params.location_state = _location_state or ""
    params.location_city = _location_city or ""
    params.front_door_faces = _front_door_faces or "S"
    params.construction_type = _construction_type or "SINGLE_FAMILY"
    params.project_type = _project_type or "NEW_CONSTRUCTION"
    params.iecc_code = _iecc_code or "IECC2021"
    params.compliance_mode = _compliance_mode or "UA"
    params.duct_location = _duct_location or "CONDITIONED_SPACE_ONLY"
    params.all_electric = bool(_all_electric) if _all_electric is not None else True
    params.has_heat_pump = bool(_has_heat_pump) if _has_heat_pump is not None else True

    if model_.user_data is None:
        model_.user_data = {}
    model_.user_data['rescheck'] = params.to_dict()
