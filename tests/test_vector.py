"""Unit tests for the immutable 3D vector algebra module (`solar_system.vector`)."""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pytest
from solar_system.vector import Vec3


def test_vec3_defaults_and_zero_constant() -> None:
    """Verify default Vec3() construction and Vec3.ZERO class constant equal (0.0, 0.0, 0.0)."""
    # Arrange
    expected = Vec3(0.0, 0.0, 0.0)

    # Act
    v_default = Vec3()
    zero_const = Vec3.ZERO

    # Assert
    assert v_default == expected
    assert zero_const == expected
    assert (v_default.x, v_default.y, v_default.z) == (0.0, 0.0, 0.0)


def test_vec3_immutability_and_slots() -> None:
    """Verify Vec3 instances are frozen (immutable) and use slotted storage without __dict__."""
    # Arrange
    v = Vec3(1.0, 2.0, 3.0)

    # Act & Assert
    with pytest.raises(FrozenInstanceError):
        v.x = 5.0  # type: ignore[misc]
    assert not hasattr(v, "__dict__")


def test_vec3_addition_subtraction_negation() -> None:
    """Verify component-wise vector addition, subtraction, and unary negation."""
    # Arrange
    a = Vec3(1.0, -2.0, 3.5)
    b = Vec3(4.0, 5.0, -1.5)

    # Act
    sum_ab = a + b
    diff_ab = a - b
    neg_a = -a

    # Assert
    assert sum_ab == Vec3(5.0, 3.0, 2.0)
    assert diff_ab == Vec3(-3.0, -7.0, 5.0)
    assert neg_a == Vec3(-1.0, 2.0, -3.5)


def test_vec3_scalar_mul_rmul_truediv_and_zero_div() -> None:
    """Verify right/left scalar multiplication, scalar division, and division-by-zero error."""
    # Arrange
    v = Vec3(2.0, -4.0, 6.0)

    # Act
    right_scaled = v * 2.5
    left_scaled = 2.5 * v
    int_scaled = 3 * v
    divided = v / 2.0

    # Assert
    assert right_scaled == Vec3(5.0, -10.0, 15.0)
    assert left_scaled == Vec3(5.0, -10.0, 15.0)
    assert int_scaled == Vec3(6.0, -12.0, 18.0)
    assert divided == Vec3(1.0, -2.0, 3.0)
    with pytest.raises(ZeroDivisionError):
        _ = v / 0.0


def test_vec3_dot_and_cross_products() -> None:
    """Verify Euclidean dot product, right-handed cross product, and orthogonality."""
    # Arrange
    ex = Vec3(1.0, 0.0, 0.0)
    ey = Vec3(0.0, 1.0, 0.0)
    ez = Vec3(0.0, 0.0, 1.0)
    u = Vec3(1.0, 2.0, 3.0)
    w = Vec3(4.0, -5.0, 6.0)

    # Act
    ortho_dot = ex.dot(ey)
    general_dot = u.dot(w)
    cross_xy = ex.cross(ey)
    cross_yx = ey.cross(ex)
    cross_uw = u.cross(w)

    # Assert
    assert ortho_dot == 0.0
    assert general_dot == 12.0
    assert cross_xy == ez
    assert cross_yx == -ez
    assert cross_uw == Vec3(27.0, 6.0, -13.0)
    assert cross_uw.dot(u) == pytest.approx(0.0, abs=1e-12)
    assert cross_uw.dot(w) == pytest.approx(0.0, abs=1e-12)


def test_vec3_norm_and_normalized_including_zero() -> None:
    """Verify squared norm, Euclidean norm, unit normalization, and safe zero-vector handling."""
    # Arrange
    v = Vec3(3.0, 4.0, 12.0)
    zero_vec = Vec3(0.0, 0.0, 0.0)

    # Act
    n_sq = v.norm_sq()
    n_val = v.norm()
    unit_v = v.normalized()
    zero_normed = zero_vec.normalized()

    # Assert
    assert n_sq == 169.0
    assert n_val == 13.0
    assert unit_v.norm() == pytest.approx(1.0, abs=1e-12)
    assert unit_v.x == pytest.approx(3.0 / 13.0, abs=1e-12)
    assert unit_v.y == pytest.approx(4.0 / 13.0, abs=1e-12)
    assert unit_v.z == pytest.approx(12.0 / 13.0, abs=1e-12)
    assert zero_normed == Vec3.ZERO


def test_vec3_rotate_z_and_rotate_x_orthogonal_and_norm_preservation() -> None:
    """Verify active right-handed 3D rotations around Z and X axes and norm preservation."""
    # Arrange
    vx = Vec3(1.0, 0.0, 0.0)
    vy = Vec3(0.0, 1.0, 0.0)
    arbitrary = Vec3(3.2, -1.7, 4.5)

    # Act
    rot_z_90 = vx.rotate_z(math.pi / 2.0)
    rot_z_180 = vx.rotate_z(math.pi)
    rot_x_90 = vy.rotate_x(math.pi / 2.0)
    rot_x_360 = vy.rotate_x(math.tau)
    chained = arbitrary.rotate_z(0.73).rotate_x(-1.12).rotate_z(2.05)

    # Assert
    assert rot_z_90.x == pytest.approx(0.0, abs=1e-12)
    assert rot_z_90.y == pytest.approx(1.0, abs=1e-12)
    assert rot_z_90.z == pytest.approx(0.0, abs=1e-12)
    assert rot_z_180.x == pytest.approx(-1.0, abs=1e-12)
    assert rot_z_180.y == pytest.approx(0.0, abs=1e-12)
    assert rot_x_90.x == pytest.approx(0.0, abs=1e-12)
    assert rot_x_90.y == pytest.approx(0.0, abs=1e-12)
    assert rot_x_90.z == pytest.approx(1.0, abs=1e-12)
    assert rot_x_360.y == pytest.approx(1.0, abs=1e-12)
    assert rot_x_360.z == pytest.approx(0.0, abs=1e-12)
    assert chained.norm() == pytest.approx(arbitrary.norm(), abs=1e-12)


def test_vec3_xy_projection() -> None:
    """Verify xy() returns the 2D ecliptic projection tuple (x, y)."""
    # Arrange
    v = Vec3(7.5, -3.25, 99.0)

    # Act
    xy_tuple = v.xy()

    # Assert
    assert xy_tuple == (7.5, -3.25)
