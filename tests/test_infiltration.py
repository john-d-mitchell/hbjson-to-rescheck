"""Tests for rescheck.infiltration."""
import pytest
from rescheck.infiltration import ach50_to_natural


def test_ach50_ten():
    assert ach50_to_natural(10.0) == pytest.approx(0.5)


def test_ach50_six():
    assert ach50_to_natural(6.0) == pytest.approx(0.3)


def test_ach50_zero():
    assert ach50_to_natural(0.0) == pytest.approx(0.0)


def test_ach50_rounds_to_three():
    # 1 / 20 = 0.05 exactly; 7 / 20 = 0.35 exactly
    assert ach50_to_natural(7.0) == pytest.approx(0.35)
    # 3 / 20 = 0.15 — checks rounding precision
    result = ach50_to_natural(3.0)
    assert result == pytest.approx(0.15)
    assert len(str(result).split(".")[-1]) <= 3


def test_ach50_typical_passive_house():
    # 0.6 ACH50 → 0.030
    assert ach50_to_natural(0.6) == pytest.approx(0.03)
