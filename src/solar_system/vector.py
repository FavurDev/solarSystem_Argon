"""Immutable 3D Euclidean vector algebra and active Euler axis rotations.

Provides the frozen slotted ``Vec3`` value object supporting component-wise
vector arithmetic, dot and cross products, Euclidean norms, safe zero-vector
normalization, active right-handed 3D rotations around the X and Z axes, and
2D ecliptic plane projection.
"""

# CHANGELOG:
# - Sprint 1: Created immutable Vec3 3D Cartesian vector and active rotation helpers.

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Vec3:
    """Immutable 3D Cartesian vector in astronomical or local reference frames.

    Attributes:
        x: Cartesian X component (default 0.0).
        y: Cartesian Y component (default 0.0).
        z: Cartesian Z component (default 0.0).
        ZERO: Shared zero-vector constant ``Vec3(0.0, 0.0, 0.0)``.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    ZERO: ClassVar[Vec3]

    def __add__(self, other: Vec3) -> Vec3:
        """Return the component-wise vector sum ``self + other``.

        Args:
            other: Vector operand to add.

        Returns:
            New ``Vec3`` representing ``(self.x + other.x, self.y + other.y, self.z + other.z)``.
        """
        if not isinstance(other, Vec3):
            return NotImplemented
        return Vec3(
            x=self.x + other.x,
            y=self.y + other.y,
            z=self.z + other.z,
        )

    def __sub__(self, other: Vec3) -> Vec3:
        """Return the component-wise vector difference ``self - other``.

        Args:
            other: Vector operand to subtract.

        Returns:
            New ``Vec3`` representing ``(self.x - other.x, self.y - other.y, self.z - other.z)``.
        """
        if not isinstance(other, Vec3):
            return NotImplemented
        return Vec3(
            x=self.x - other.x,
            y=self.y - other.y,
            z=self.z - other.z,
        )

    def __mul__(self, scalar: float) -> Vec3:
        """Return the right scalar product ``self * scalar``.

        Args:
            scalar: Real numeric factor by which to scale each coordinate.

        Returns:
            New ``Vec3`` scaled by ``scalar``.
        """
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        s = float(scalar)
        return Vec3(
            x=self.x * s,
            y=self.y * s,
            z=self.z * s,
        )

    def __rmul__(self, scalar: float) -> Vec3:
        """Return the left scalar product ``scalar * self``.

        Args:
            scalar: Real numeric factor by which to scale each coordinate.

        Returns:
            New ``Vec3`` scaled by ``scalar``.
        """
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vec3:
        """Return the scalar quotient ``self / scalar``.

        Args:
            scalar: Non-zero real divisor.

        Returns:
            New ``Vec3`` divided component-wise by ``scalar``.

        Raises:
            ZeroDivisionError: If ``scalar == 0.0``.
        """
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        s = float(scalar)
        if s == 0.0:
            raise ZeroDivisionError("Cannot divide Vec3 by zero")
        return Vec3(
            x=self.x / s,
            y=self.y / s,
            z=self.z / s,
        )

    def __neg__(self) -> Vec3:
        """Return the unary negation ``-self``.

        Returns:
            New ``Vec3`` with each component negated.
        """
        return Vec3(
            x=-self.x,
            y=-self.y,
            z=-self.z,
        )

    def dot(self, other: Vec3) -> float:
        """Compute the 3D Euclidean dot product ``self . other``.

        Args:
            other: Second 3D vector operand.

        Returns:
            Scalar dot product ``self.x * other.x + self.y * other.y + self.z * other.z``.
        """
        return (self.x * other.x) + (self.y * other.y) + (self.z * other.z)

    def cross(self, other: Vec3) -> Vec3:
        """Compute the right-handed 3D cross product ``self x other``.

        Args:
            other: Second 3D vector operand.

        Returns:
            New ``Vec3`` orthogonal to both ``self`` and ``other``.
        """
        return Vec3(
            x=(self.y * other.z) - (self.z * other.y),
            y=(self.z * other.x) - (self.x * other.z),
            z=(self.x * other.y) - (self.y * other.x),
        )

    def norm_sq(self) -> float:
        """Compute the squared Euclidean norm ``x^2 + y^2 + z^2``.

        Returns:
            Non-negative squared length of the vector.
        """
        return (self.x * self.x) + (self.y * self.y) + (self.z * self.z)

    def norm(self) -> float:
        """Compute the Euclidean norm ``sqrt(x^2 + y^2 + z^2)``.

        Returns:
            Non-negative Euclidean length of the vector.
        """
        return math.sqrt(self.norm_sq())

    def normalized(self) -> Vec3:
        """Return the unit vector in the direction of ``self``, or ``Vec3.ZERO`` if zero.

        Returns:
            Unit-length ``Vec3`` when ``self.norm() > 0.0``, otherwise ``Vec3.ZERO``.
        """
        length = self.norm()
        if length == 0.0:
            return Vec3.ZERO
        return self / length

    def rotate_x(self, angle_rad: float) -> Vec3:
        """Actively rotate this vector around the +X axis by ``angle_rad`` radians.

        Args:
            angle_rad: Counter-clockwise rotation angle in radians about +X.

        Returns:
            Rotated ``Vec3`` with preserved Euclidean norm.
        """
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return Vec3(
            x=self.x,
            y=(self.y * c) - (self.z * s),
            z=(self.y * s) + (self.z * c),
        )

    def rotate_z(self, angle_rad: float) -> Vec3:
        """Actively rotate this vector around the +Z axis by ``angle_rad`` radians.

        Args:
            angle_rad: Counter-clockwise rotation angle in radians about +Z.

        Returns:
            Rotated ``Vec3`` with preserved Euclidean norm.
        """
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return Vec3(
            x=(self.x * c) - (self.y * s),
            y=(self.x * s) + (self.y * c),
            z=self.z,
        )

    def xy(self) -> tuple[float, float]:
        """Return the 2D ecliptic plane projection ``(x, y)``.

        Returns:
            Two-element tuple ``(self.x, self.y)``.
        """
        return (self.x, self.y)


Vec3.ZERO = Vec3(0.0, 0.0, 0.0)
