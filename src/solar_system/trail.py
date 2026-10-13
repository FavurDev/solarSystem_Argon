"""Bounded FIFO trajectory ring buffer and immutable orbital point value type.

This module provides pure-Python trajectory storage for celestial bodies:
- ``OrbitPoint``: Immutable 2D ecliptic position sample in Astronomical Units
  paired with its Julian Date timestamp.
- ``TrailBuffer``: Bounded first-in-first-out ring buffer backed by
  ``collections.deque`` that automatically evicts oldest samples when full and
  clears all stored points whenever the active reference frame changes.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

DEFAULT_MAX_TRAIL_POINTS: int = 480
DEFAULT_FRAME_NAME: str = "Sun"

__all__ = [
    "DEFAULT_FRAME_NAME",
    "DEFAULT_MAX_TRAIL_POINTS",
    "OrbitPoint",
    "TrailBuffer",
]


@dataclass(frozen=True, slots=True)
class OrbitPoint:
    """Immutable 2D orbital position sample in Astronomical Units with Julian Date.

    Attributes:
        x_au: Horizontal ecliptic coordinate in Astronomical Units relative to
            the active reference frame origin.
        y_au: Vertical ecliptic coordinate in Astronomical Units relative to
            the active reference frame origin.
        jd: Simulation Julian Date epoch at which the sample was recorded.
    """

    x_au: float
    y_au: float
    jd: float


class TrailBuffer:
    """Bounded FIFO ring buffer storing a body's orbital trail in a reference frame.

    Backed by ``collections.deque`` with ``maxlen=max_points`` for O(1) appends
    and automatic oldest-sample eviction. Switching the coordinate reference
    frame automatically clears all prior samples before recording the new point.
    """

    def __init__(
        self,
        max_points: int = DEFAULT_MAX_TRAIL_POINTS,
        frame_name: str = DEFAULT_FRAME_NAME,
    ) -> None:
        """Initialize a bounded trajectory ring buffer.

        Args:
            max_points: Maximum number of ``OrbitPoint`` samples retained in the
                buffer. Must be >= 2.
            frame_name: Identifier of the initial coordinate reference frame.

        Raises:
            ValueError: If ``max_points < 2``.
        """
        if max_points < 2:
            raise ValueError(f"max_points must be >= 2, got {max_points}")
        self._max_points: int = max_points
        self._frame_name: str = frame_name
        # IMPLEMENTATION DECISION: Use collections.deque(maxlen=max_points).
        # Rationale: O(1) append and automatic FIFO eviction in C-backed stdlib deque.
        # Alternatives: Python list with pop(0)/slice deletion (O(N)), numpy ring array.
        self._points: deque[OrbitPoint] = deque(maxlen=max_points)

    @property
    def max_points(self) -> int:
        """Return the maximum number of points retained by the buffer."""
        return self._max_points

    @property
    def frame_name(self) -> str:
        """Return the active reference frame name for buffered points."""
        return self._frame_name

    def append(self, x_au: float, y_au: float, jd: float, frame_name: str) -> None:
        """Record a new orbital position sample into the ring buffer.

        If ``frame_name`` differs from the current ``self.frame_name``, all
        previously buffered points are cleared and ``self.frame_name`` is updated
        before appending the new sample.

        Args:
            x_au: Ecliptic X coordinate in Astronomical Units.
            y_au: Ecliptic Y coordinate in Astronomical Units.
            jd: Simulation Julian Date epoch of the sample.
            frame_name: Coordinate reference frame in which the sample was measured.
        """
        if frame_name != self._frame_name:
            self.clear()
            self._frame_name = frame_name
        self._points.append(OrbitPoint(x_au=x_au, y_au=y_au, jd=jd))

    def clear(self) -> None:
        """Remove all stored ``OrbitPoint`` samples while preserving capacity and frame."""
        self._points.clear()

    def points(self) -> tuple[OrbitPoint, ...]:
        """Return an immutable snapshot of buffered points ordered oldest-to-newest.

        Returns:
            A tuple of ``OrbitPoint`` instances from oldest (index 0) to newest.
        """
        return tuple(self._points)

    def __len__(self) -> int:
        """Return the number of ``OrbitPoint`` samples currently stored."""
        return len(self._points)
