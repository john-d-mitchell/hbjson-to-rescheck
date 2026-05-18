"""Tests for rescheck.units."""
import pytest
from rescheck.units import m2_to_ft2, m_to_ft


def test_m2_to_ft2_one():
    assert m2_to_ft2(1.0) == pytest.approx(10.7639)


def test_m2_to_ft2_zero():
    assert m2_to_ft2(0.0) == pytest.approx(0.0)


def test_m2_to_ft2_value():
    assert m2_to_ft2(10.0) == pytest.approx(107.639)


def test_m_to_ft_one():
    assert m_to_ft(1.0) == pytest.approx(3.28084)


def test_m_to_ft_zero():
    assert m_to_ft(0.0) == pytest.approx(0.0)


def test_m_to_ft_value():
    assert m_to_ft(3.048) == pytest.approx(10.0, rel=1e-4)
