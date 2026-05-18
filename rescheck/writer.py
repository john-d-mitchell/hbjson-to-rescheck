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
    """Convert Python bool / truthy to lowercase XML boolean string."""
    return "true" if value else "false"


def _cdata(text: str) -> str:
    """Wrap text in a CDATA section."""
    return "<![CDATA[{}]]>".format(text.replace("]]>", "]]]]><![CDATA[>"))


def _escape(text: str) -> str:
    """HTML-escape text for use in XML element content."""
    return html.escape(str(text))


def _window_xml(win, list_position: int) -> str:
    gt = _glazing_type(win.u_value)
    return (
        "            <windows>\n"
        "                <listPosition>{pos}</listPosition>\n"
        "                <glazingType>{gt}</glazingType>\n"
        "                <glazingArea>{area:.3f}</glazingArea>\n"
        "                <glazingUValue>{u:.4f}</glazingUValue>\n"
        "                <glazingSHGC>{shgc:.4f}</glazingSHGC>\n"
        "                <windowHeight>{h:.3f}</windowHeight>\n"
        "                <windowOrientation>{orient}</windowOrientation>\n"
        "            </windows>\n"
    ).format(
        pos=list_position,
        gt=gt,
        area=win.area_ft2,
        u=win.u_value,
        shgc=win.shgc,
        h=win.height_ft,
        orient=win.orientation,
    )


def _door_xml(door) -> str:
    return (
        "            <doors>\n"
        "                <doorArea>{area:.3f}</doorArea>\n"
        "                <doorUValue>{u:.4f}</doorUValue>\n"
        "                <doorOrientation>{orient}</doorOrientation>\n"
        "            </doors>\n"
    ).format(
        area=door.area_ft2,
        u=door.u_value,
        orient=door.orientation,
    )


def _above_grade_wall_xml(wall, list_pos: int) -> str:
    lines = [
        "        <aboveGroundWalls>\n",
        "            <listPosition>{}</listPosition>\n".format(list_pos),
        "            <wallOrientation>{}</wallOrientation>\n".format(wall.orientation),
        "            <wallHeight>{:.3f}</wallHeight>\n".format(wall.wall_height_ft),
        "            <wallGrossArea>{:.3f}</wallGrossArea>\n".format(wall.gross_area_ft2),
        "            <wallCavityR>{:.2f}</wallCavityR>\n".format(wall.cavity_r),
        "            <wallContinuousR>{:.2f}</wallContinuousR>\n".format(wall.continuous_r),
        "            <wallUValue>{:.4f}</wallUValue>\n".format(wall.u_value),
    ]
    for i, win in enumerate(wall.windows):
        lines.append(_window_xml(win, 0))
    for door in wall.doors:
        lines.append(_door_xml(door))
    lines.append("        </aboveGroundWalls>\n")
    return "".join(lines)


def _below_grade_wall_xml(wall, list_pos: int) -> str:
    lines = [
        "        <belowGroundWalls>\n",
        "            <listPosition>{}</listPosition>\n".format(list_pos),
        "            <wallOrientation>{}</wallOrientation>\n".format(wall.orientation),
        "            <wallGrossArea>{:.3f}</wallGrossArea>\n".format(wall.gross_area_ft2),
        "            <wallHeight>{:.3f}</wallHeight>\n".format(wall.wall_height_ft),
        "            <wallBelowGradeHeight>{:.3f}</wallBelowGradeHeight>\n".format(
            wall.below_grade_height_ft
        ),
        "            <wallCavityR>{:.2f}</wallCavityR>\n".format(wall.cavity_r),
        "            <wallContinuousR>{:.2f}</wallContinuousR>\n".format(wall.continuous_r),
        "            <wallUValue>{:.4f}</wallUValue>\n".format(wall.u_value),
    ]
    for win in wall.windows:
        lines.append(_window_xml(win, 0))
    for door in wall.doors:
        lines.append(_door_xml(door))
    lines.append("        </belowGroundWalls>\n")
    return "".join(lines)


def _roof_xml(roof, list_pos: int) -> str:
    return (
        "        <roofs>\n"
        "            <listPosition>{pos}</listPosition>\n"
        "            <roofType>{rt}</roofType>\n"
        "            <roofGrossArea>{area:.3f}</roofGrossArea>\n"
        "            <roofCavityR>{cr:.2f}</roofCavityR>\n"
        "            <roofContinuousR>{ccr:.2f}</roofContinuousR>\n"
        "            <roofUValue>{u:.4f}</roofUValue>\n"
        "        </roofs>\n"
    ).format(
        pos=list_pos,
        rt=roof.roof_type,
        area=roof.gross_area_ft2,
        cr=roof.cavity_r,
        ccr=roof.continuous_r,
        u=roof.u_value,
    )


def _floor_xml(floor, list_pos: int) -> str:
    return (
        "        <floors>\n"
        "            <listPosition>{pos}</listPosition>\n"
        "            <floorType>{ft}</floorType>\n"
        "            <floorGrossArea>{area:.3f}</floorGrossArea>\n"
        "            <floorCavityR>{cr:.2f}</floorCavityR>\n"
        "        </floors>\n"
    ).format(
        pos=list_pos,
        ft=floor.floor_type,
        area=floor.gross_area_ft2,
        cr=floor.cavity_r,
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
    loc_state = location.get("state", "")
    loc_city = location.get("city", "")

    # Build envelope XML fragment
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
        "        <projectState>{state_esc}</projectState>\n"
        "        <projectZip>{zip_esc}</projectZip>\n"
        "        <ownerName>{owner_cdata}</ownerName>\n"
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
        state_esc=_escape(state),
        zip_esc=_escape(zip_code),
        owner_cdata=_cdata(owner_name),
        envelope_section=envelope_section,
        ach=infiltration_ach,
        iecc_code=_escape(iecc_code),
        compliance_mode=_escape(compliance_mode),
    )

    return xml
