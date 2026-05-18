"""Infiltration conversion utilities."""


def ach50_to_natural(ach50: float) -> float:
    """Convert ACH50 blower-door result to estimated natural ACH.

    Uses the conventional divide-by-20 rule of thumb for residential buildings.

    Args:
        ach50: Air changes per hour at 50 Pa.

    Returns:
        Estimated natural air changes per hour, rounded to 3 decimal places.
    """
    return round(ach50 / 20.0, 3)
