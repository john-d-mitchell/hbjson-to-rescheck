"""Assembly R-value classification utilities.

Reads honeybee construction layer dicts and splits thermal resistance into
cavity R-value and continuous (ci) R-value in imperial units.
"""

# SI R-value (m²·K/W) → IP R-value (ft²·°F·h/BTU)
_SI_TO_IP_R = 5.678


def _layer_r_si(layer: dict) -> float:
    """Return layer R-value in SI (m²·K/W)."""
    r = layer.get("r_value")
    if r is not None:
        return float(r)
    conductivity = layer.get("conductivity")
    thickness = layer.get("thickness")
    if conductivity and thickness and float(conductivity) > 0:
        return float(thickness) / float(conductivity)
    return 0.0

# Keywords that identify cavity insulation layers (case-insensitive)
_CAVITY_KEYWORDS = (
    "batt",
    "cavity",
    "mineral",
    "cellulose",
    "fiberglass",
    "rockwool",
    "spray",
    "ocspf",
    "blown",
)

# Keywords that identify continuous (ci) insulation layers (case-insensitive)
_CONTINUOUS_KEYWORDS = (
    "rigid",
    "xps",
    "eps",
    "polyiso",
    "polyisocyanurate",
    "foam_board",
    "continuous",
    "ci",
)

# Standard ASHRAE air film resistances (IP units, ft²·°F·h/BTU)
_INTERIOR_AIR_FILM_IP = 0.68
_EXTERIOR_AIR_FILM_IP = 0.17


def _is_cavity(identifier: str) -> bool:
    lower = identifier.lower()
    return any(kw in lower for kw in _CAVITY_KEYWORDS)


def _is_continuous(identifier: str) -> bool:
    lower = identifier.lower()
    return any(kw in lower for kw in _CONTINUOUS_KEYWORDS)


def classify_layers(layers: list) -> tuple:
    """Split assembly layers into cavity and continuous R-values (imperial).

    Args:
        layers: List of EnergyMaterial dicts, each with at least
                ``identifier`` (str) and ``r_value`` (float, m²·K/W).

    Returns:
        (cavity_r_ip, continuous_r_ip) — both in ft²·°F·h/BTU.
    """
    cavity_r_ip = 0.0
    continuous_r_ip = 0.0

    for layer in layers:
        identifier = layer.get("identifier", "")
        r_si = _layer_r_si(layer)
        r_ip = r_si * _SI_TO_IP_R

        if _is_cavity(identifier):
            cavity_r_ip += r_ip
        elif _is_continuous(identifier):
            continuous_r_ip += r_ip
        # else: structural/finish layer — excluded from both

    return (cavity_r_ip, continuous_r_ip)


def assembly_u_value(layers: list) -> float:
    """Compute total assembly U-value in imperial units.

    Includes all layers (cavity + continuous + structural/finish) plus
    standard ASHRAE interior and exterior air films.

    U = 1 / (R_total_ip + 0.68 + 0.17)

    Args:
        layers: List of EnergyMaterial dicts with ``r_value`` (m²·K/W).

    Returns:
        U-value in BTU/(ft²·°F·h).
    """
    total_r_ip = sum(_layer_r_si(layer) * _SI_TO_IP_R for layer in layers)
    total_r_ip += _INTERIOR_AIR_FILM_IP + _EXTERIOR_AIR_FILM_IP
    if total_r_ip == 0.0:
        return 0.0
    return 1.0 / total_r_ip
