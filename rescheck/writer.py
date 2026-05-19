"""ResCheck RXL XML writer.

Generates a ResCheck-compatible RXL file from EnvelopeData and project metadata.
Uses f-string XML construction (no lxml required) to support duplicate sibling
tag names that xml.etree.ElementTree cannot handle natively.
"""

import html


def _glazing_type(u_value_ip: float) -> str:
    """Derive glazing type from U-value (BTU/h·ft²·°F)."""
    if u_value_ip <= 0.22:
        return "TRIPLE"
    elif u_value_ip <= 0.32:
        return "DOUBLE"
    else:
        return "SINGLE"


def _bool_str(value) -> str:
    return "true" if value else "false"


def _cdata(text: str) -> str:
    return "<![CDATA[{}]]>".format(text.replace("]]>", "]]]]><![CDATA[>"))


def _escape(text: str) -> str:
    return html.escape(str(text))


def _window_xml(win, list_position: int) -> str:
    gt = _glazing_type(win.u_value)
    return (
        "                <window>\n"
        "                    <glazingType>{gt}</glazingType>\n"
        "                    <glazingMaterialType>GLASS_GLAZING_MAT</glazingMaterialType>\n"
        "                    <frameType>OTHER_FRAME</frameType>\n"
        "                    <propShgc>{shgc:.2f}</propShgc>\n"
        "                    <pfGlazingWidth>0.00</pfGlazingWidth>\n"
        "                    <pfGlazingHeight>{h:.2f}</pfGlazingHeight>\n"
        "                    <propProjectionFactor>0.00</propProjectionFactor>\n"
        "                    <listPosition>{pos}</listPosition>\n"
        "                    <description>{desc}</description>\n"
        "                    <assemblyType>{atype}</assemblyType>\n"
        "                    <propUvalue>{u:.3f}</propUvalue>\n"
        "                    <relOrientation>{orient}</relOrientation>\n"
        "                    <grossArea>{area:.2f}</grossArea>\n"
        "                </window>\n"
    ).format(
        gt=gt,
        shgc=win.shgc,
        h=win.height_ft,
        pos=list_position,
        desc=_cdata("Other"),
        atype=_cdata("Window 1"),
        u=win.u_value,
        orient=win.orientation,
        area=win.area_ft2,
    )


def _door_xml(door, list_position: int) -> str:
    return (
        "                <door>\n"
        "                    <doorType>OPAQUE_DOOR</doorType>\n"
        "                    <listPosition>{pos}</listPosition>\n"
        "                    <description>{desc}</description>\n"
        "                    <assemblyType>{atype}</assemblyType>\n"
        "                    <propUvalue>{u:.3f}</propUvalue>\n"
        "                    <relOrientation>{orient}</relOrientation>\n"
        "                    <grossArea>{area:.2f}</grossArea>\n"
        "                </door>\n"
    ).format(
        pos=list_position,
        desc=_cdata("Solid"),
        atype=_cdata("Door 1"),
        u=door.u_value,
        orient=door.orientation,
        area=door.area_ft2,
    )


def _windows_block(windows) -> str:
    if not windows:
        return ""
    lines = ["                <windows>\n"]
    for i, win in enumerate(windows):
        lines.append(_window_xml(win, i))
    lines.append("                </windows>\n")
    return "".join(lines)


def _doors_block(doors) -> str:
    if not doors:
        return ""
    lines = ["                <doors>\n"]
    for i, door in enumerate(doors):
        lines.append(_door_xml(door, i))
    lines.append("                </doors>\n")
    return "".join(lines)


def _above_grade_wall_xml(wall, list_pos: int) -> str:
    lines = [
        "        <aboveGroundWalls>\n",
        "            <agWall>\n",
        "                <wallType>OTHER_AG_WALL</wallType>\n",
        "                <otherWallType>AG_WALL_OTHER_OTHER</otherWallType>\n",
        "                <listPosition>{}</listPosition>\n".format(list_pos),
        "                <description>{}</description>\n".format(_cdata("Framed wall")),
        "                <assemblyType>{}</assemblyType>\n".format(
            _cdata("Wall {}".format(list_pos))
        ),
        "                <propUvalue>{:.3f}</propUvalue>\n".format(wall.u_value),
        "                <cavityRvalue>{:.2f}</cavityRvalue>\n".format(wall.cavity_r),
        "                <continuousRvalue>{:.2f}</continuousRvalue>\n".format(wall.continuous_r),
        "                <relOrientation>{}</relOrientation>\n".format(wall.orientation),
        "                <grossArea>{:.2f}</grossArea>\n".format(wall.gross_area_ft2),
    ]
    lines.append(_windows_block(wall.windows))
    lines.append(_doors_block(wall.doors))
    lines.append("            </agWall>\n")
    lines.append("        </aboveGroundWalls>\n")
    return "".join(lines)


def _below_grade_wall_xml(wall, list_pos: int) -> str:
    lines = [
        "        <belowGroundWalls>\n",
        "            <bgWall>\n",
        "                <insulationPosition>INTEGRAL</insulationPosition>\n",
        "                <wallType>WOOD_BG_WALL</wallType>\n",
        "                <wallHeight>{:.2f}</wallHeight>\n".format(wall.wall_height_ft),
        "                <wallHeightBelowGrade>{:.2f}</wallHeightBelowGrade>\n".format(
            wall.below_grade_height_ft
        ),
        "                <depthOfInsulation>{:.2f}</depthOfInsulation>\n".format(
            wall.wall_height_ft
        ),
        "                <listPosition>{}</listPosition>\n".format(list_pos),
        "                <description>{}</description>\n".format(_cdata("Wood Frame")),
        "                <assemblyType>{}</assemblyType>\n".format(
            _cdata("Basement Wall {}".format(list_pos))
        ),
        "                <cavityRvalue>{:.2f}</cavityRvalue>\n".format(wall.cavity_r),
        "                <continuousRvalue>{:.2f}</continuousRvalue>\n".format(wall.continuous_r),
        "                <relOrientation>{}</relOrientation>\n".format(wall.orientation),
        "                <grossArea>{:.2f}</grossArea>\n".format(wall.gross_area_ft2),
    ]
    lines.append(_windows_block(wall.windows))
    lines.append(_doors_block(wall.doors))
    lines.append("            </bgWall>\n")
    lines.append("        </belowGroundWalls>\n")
    return "".join(lines)


def _roof_xml(roof, list_pos: int) -> str:
    return (
        "        <roofs>\n"
        "            <roof>\n"
        "                <roofType>{rt}</roofType>\n"
        "                <roofInsulType>ROOF_INSUL_TYPE_UNSPECIFIED</roofInsulType>\n"
        "                <listPosition>{pos}</listPosition>\n"
        "                <description>{desc}</description>\n"
        "                <assemblyType>{atype}</assemblyType>\n"
        "                <cavityRvalue>{cr:.2f}</cavityRvalue>\n"
        "                <continuousRvalue>{ccr:.2f}</continuousRvalue>\n"
        "                <propUvalue>{u:.3f}</propUvalue>\n"
        "                <grossArea>{area:.2f}</grossArea>\n"
        "            </roof>\n"
        "        </roofs>\n"
    ).format(
        rt=roof.roof_type,
        pos=list_pos,
        desc=_cdata("Cathedral Ceiling (no attic)"),
        atype=_cdata("Ceiling {}".format(list_pos)),
        cr=roof.cavity_r,
        ccr=roof.continuous_r,
        u=roof.u_value,
        area=roof.gross_area_ft2,
    )


def _floor_xml(floor, list_pos: int) -> str:
    return (
        "        <floors>\n"
        "            <floor>\n"
        "                <floorType>{ft}</floorType>\n"
        "                <depthOfInsulation>2.00</depthOfInsulation>\n"
        "                <insulationPosition>NO_INSULATION</insulationPosition>\n"
        "                <listPosition>{pos}</listPosition>\n"
        "                <description>{desc}</description>\n"
        "                <assemblyType>{atype}</assemblyType>\n"
        "                <cavityRvalue>{cr:.2f}</cavityRvalue>\n"
        "                <grossArea>{area:.2f}</grossArea>\n"
        "            </floor>\n"
        "        </floors>\n"
    ).format(
        ft=floor.floor_type,
        pos=list_pos,
        desc=_cdata("All-Wood Joist/Truss:Over Outside Air"),
        atype=_cdata("Floor {}".format(list_pos)),
        cr=floor.cavity_r,
        area=floor.gross_area_ft2,
    )


def write_rxl(envelope, metadata: dict, infiltration_ach: float) -> str:
    """Generate a ResCheck RXL XML string.

    Args:
        envelope: EnvelopeData instance from rescheck.envelope.
        metadata: The ``rescheck`` metadata dict (from user_data or properties).
        infiltration_ach: Natural air changes per hour.

    Returns:
        XML string ready to write to a .rxl file.
    """
    building = metadata.get("building", {})
    project = metadata.get("project", {})
    owner = metadata.get("owner", {})
    location = metadata.get("location", {})

    project_type = building.get("project_type", "NEW_CONSTRUCTION")
    construction_type = building.get("construction_type", "SINGLE_FAMILY")
    duct_location = building.get("duct_location", "CONDITIONED_SPACE_ONLY")
    all_electric = _bool_str(building.get("all_electric", False))
    has_heat_pump = _bool_str(building.get("has_heat_pump", False))
    iecc_code = building.get("iecc_code", "IECC2021")
    compliance_mode = building.get("compliance_mode", "UA")

    title = project.get("title", "")
    address = project.get("address", "")
    city = project.get("city", "")
    state = project.get("state", "")
    zip_code = project.get("zip", "")

    owner_name = owner.get("name", "")
    owner_address = owner.get("address", "")
    owner_city = owner.get("city", "")
    owner_state = owner.get("state", state)
    owner_zip = owner.get("zip", zip_code)

    loc_state = location.get("state", "")
    loc_city = location.get("city", "")

    # Build envelope XML
    envelope_lines = [
        "    <envelope>\n",
        "        <useOrientDetails>true</useOrientDetails>\n",
        "        <useProjectionFactorDetails>false</useProjectionFactorDetails>\n",
    ]

    wall_pos = 1
    for wall in envelope.walls:
        if wall.is_below_grade:
            envelope_lines.append(_below_grade_wall_xml(wall, wall_pos))
        else:
            envelope_lines.append(_above_grade_wall_xml(wall, wall_pos))
        wall_pos += 1

    for i, roof in enumerate(envelope.roofs, 1):
        envelope_lines.append(_roof_xml(roof, i))

    for i, floor in enumerate(envelope.floors, 1):
        envelope_lines.append(_floor_xml(floor, i))

    envelope_lines.append("    </envelope>\n")
    envelope_section = "".join(envelope_lines)

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<building xmlns="http://energycode.pnl.gov/ns/ResCheckBuildingSchema"'
        ' xmlns:xs="http://www.w3.org/2001/XMLSchema-instance">\n'
        "    <projectType>{project_type}</projectType>\n"
        "    <projectSubType>CONSTRUCTION_NONE</projectSubType>\n"
        "    <energyCreditExceptionType>ENERGY_CREDIT_EXCEPTION_NONE</energyCreditExceptionType>\n"
        "    <buildingOrientation>0.00</buildingOrientation>\n"
        "    <ductLocationType>{duct_location}</ductLocationType>\n"
        "    <ductLocation2Type>DUCT_LOCATION_TYPE_UNKNOWN</ductLocation2Type>\n"
        "    <conditionedFloorArea>{cfa:.3f}</conditionedFloorArea>\n"
        "    <isPoolSystem>false</isPoolSystem>\n"
        "    <isFireplace>false</isFireplace>\n"
        "    <isSunroom>false</isSunroom>\n"
        "    <allElectric>{all_electric}</allElectric>\n"
        "    <isRenewable>false</isRenewable>\n"
        "    <hasBattery>false</hasBattery>\n"
        "    <hasCharger>false</hasCharger>\n"
        "    <hasHeatPump>{has_heat_pump}</hasHeatPump>\n"
        "    <electricReady>false</electricReady>\n"
        "    <solarReady>false</solarReady>\n"
        "    <responsiveWaterHeating>false</responsiveWaterHeating>\n"
        "    <constructionType>{construction_type}</constructionType>\n"
        "    <location>\n"
        "        <state>{loc_state}</state>\n"
        "        <city>{loc_city}</city>\n"
        "    </location>\n"
        "    <project>\n"
        "        <projectTitle>{title_cdata}</projectTitle>\n"
        "        <projectAddress>{addr_cdata}</projectAddress>\n"
        "        <projectCity>{city_cdata}</projectCity>\n"
        "        <projectState>{state_cdata}</projectState>\n"
        "        <projectZipCode>{zip_cdata}</projectZipCode>\n"
        "        <ownerFirstName>{owner_fn_cdata}</ownerFirstName>\n"
        "        <ownerLastName>{owner_ln_cdata}</ownerLastName>\n"
        "        <ownerAddress>{owner_addr_cdata}</ownerAddress>\n"
        "        <ownerCity>{owner_city_cdata}</ownerCity>\n"
        "        <ownerState>{owner_state_cdata}</ownerState>\n"
        "        <ownerZipCode>{owner_zip_cdata}</ownerZipCode>\n"
        "        <projectComplete>false</projectComplete>\n"
        "    </project>\n"
        "{envelope_section}"
        "    <infiltration>\n"
        "        <loadsAch>{ach:.1f}</loadsAch>\n"
        "    </infiltration>\n"
        "    <control>\n"
        "        <code>{iecc_code}</code>\n"
        "        <complianceMode>{compliance_mode}</complianceMode>\n"
        "    </control>\n"
        "</building>\n"
    ).format(
        project_type=project_type,
        duct_location=duct_location,
        cfa=envelope.conditioned_floor_area_ft2,
        all_electric=all_electric,
        has_heat_pump=has_heat_pump,
        construction_type=construction_type,
        loc_state=_escape(loc_state),
        loc_city=_escape(loc_city),
        title_cdata=_cdata(title),
        addr_cdata=_cdata(address),
        city_cdata=_cdata(city),
        state_cdata=_cdata(state),
        zip_cdata=_cdata(zip_code),
        owner_fn_cdata=_cdata(owner_name),
        owner_ln_cdata=_cdata(""),
        owner_addr_cdata=_cdata(owner_address),
        owner_city_cdata=_cdata(owner_city),
        owner_state_cdata=_cdata(owner_state),
        owner_zip_cdata=_cdata(owner_zip),
        envelope_section=envelope_section,
        ach=infiltration_ach,
        iecc_code=_escape(iecc_code),
        compliance_mode=_escape(compliance_mode),
    )

    return xml
