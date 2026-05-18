"""Unit conversion utilities for SI → Imperial."""


def m2_to_ft2(value: float) -> float:
    """Convert square meters to square feet."""
    return value * 10.7639


def m_to_ft(value: float) -> float:
    """Convert meters to feet."""
    return value * 3.28084
