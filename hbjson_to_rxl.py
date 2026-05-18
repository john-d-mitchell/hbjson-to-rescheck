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

    # Support metadata from both GH component (user_data.rescheck) and
    # direct model properties (properties.rescheck)
    metadata = (
        (hbjson.get("user_data") or {}).get("rescheck")
        or hbjson.get("properties", {}).get("rescheck", {})
    )

    front_door_faces = metadata.get("building", {}).get("front_door_faces", "S")

    envelope = extract_envelope(hbjson, front_door_faces)

    ach50 = _get_ach50(hbjson)
    natural_ach = ach50_to_natural(ach50) if ach50 is not None else 0.5

    xml_str = write_rxl(envelope, metadata, natural_ach)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print("Written to {}".format(output_path))


if __name__ == "__main__":
    main()
