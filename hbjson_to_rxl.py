#!/usr/bin/env python3
"""CLI entry point: convert an hbjson file to a ResCheck RXL file.

Usage:
    python hbjson_to_rxl.py <input.hbjson> <output.rxl>
"""

import json
import sys

from rescheck.envelope import extract_envelope
from rescheck.infiltration import ach50_to_natural
from rescheck.writer import write_rxl


def _merge_ph_team(hbjson: dict, rescheck: dict) -> dict:
    """Build a unified metadata dict by merging PH team data with ResCheck overrides.

    PH team data (properties.ph.team) provides: project title, address, city,
    zip, and owner info. ResCheck metadata provides: state abbreviation, climate
    location, and compliance flags.
    """
    team = (
        hbjson.get("properties", {})
        .get("ph", {})
        .get("team", {})
    )
    ph_building = team.get("building", {})
    ph_owner = team.get("owner", {})

    rc_building = rescheck.get("building", {})
    state = rc_building.get("state", "")

    return {
        "project": {
            "title": ph_building.get("name") or "",
            "address": ph_building.get("street") or "",
            "city": ph_building.get("city") or "",
            "state": state,
            "zip": ph_building.get("post_code") or "",
        },
        "owner": {
            "name": ph_owner.get("name") or "",
            "address": ph_owner.get("street") or "",
            "city": ph_owner.get("city") or "",
            "state": state,
            "zip": ph_owner.get("post_code") or "",
        },
        "location": rescheck.get("location", {}),
        "building": rc_building,
    }


def _get_ach50(hbjson: dict) -> float | None:
    """Extract ACH50 from honeybee-ph properties.

    Tries model-level properties first, then the first room.
    """
    ph = hbjson.get("properties", {}).get("ph", {})
    if "infiltration_ach50" in ph:
        return ph["infiltration_ach50"]
    for room in hbjson.get("rooms", []):
        room_ph = room.get("properties", {}).get("ph", {})
        if "infiltration_ach50" in room_ph:
            return room_ph["infiltration_ach50"]
    return None


def main():
    if len(sys.argv) != 3:
        print("Usage: python hbjson_to_rxl.py <input.hbjson> <output.rxl>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, encoding="utf-8") as f:
        hbjson = json.load(f)

    # ResCheck-specific metadata from GH component (user_data.rescheck)
    rescheck = (
        (hbjson.get("user_data") or {}).get("rescheck")
        or hbjson.get("properties", {}).get("rescheck", {})
        or {}
    )

    # Merge PH team data (set via HBPH Set Model Project Data) into metadata
    metadata = _merge_ph_team(hbjson, rescheck)

    front_door_faces = rescheck.get("building", {}).get("front_door_faces", "S")

    envelope = extract_envelope(hbjson, front_door_faces)

    ach50 = _get_ach50(hbjson)
    natural_ach = ach50_to_natural(ach50) if ach50 is not None else 0.5

    xml_str = write_rxl(envelope, metadata, natural_ach)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print("Written to {}".format(output_path))


if __name__ == "__main__":
    main()
