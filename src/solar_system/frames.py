"""Hierarchical coordinate reference frames and parent-chain transformations.

Provides the immutable ``ReferenceFrame`` value object, the structural
``BodyLookup`` protocol, the 8-frame registry ``build_frame_registry()``,
and parent-chain position and trajectory resolvers in 3D Cartesian AU.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from solar_system.kepler import OrbitalElements, keplerian_to_cartesian
from solar_system.vector import Vec3

__all__ = [
    "BodyLookup",
    "ReferenceFrame",
    "body_trajectory_in_frame",
    "build_frame_registry",
    "heliocentric_position",
    "local_orbit_offset",
    "world_position",
    "world_positions",
]


@dataclass(frozen=True, slots=True)
class ReferenceFrame:
    """Immutable descriptor for a coordinate reference frame centered on a body.

    Args:
        name: Canonical identifier of the reference frame (e.g., ``"Sun"``).
        center_body_name: Name of the celestial body anchored at ``Vec3.ZERO``.
        description: Human-readable astronomical description of the frame.

    Raises:
        ValueError: If ``name`` or ``center_body_name`` is empty when stripped.
    """

    name: str
    center_body_name: str
    description: str

    def __post_init__(self) -> None:
        """Validate that frame name and center body name are non-empty."""
        if not self.name.strip():
            raise ValueError("ReferenceFrame.name must be non-empty.")
        if not self.center_body_name.strip():
            raise ValueError("ReferenceFrame.center_body_name must be non-empty.")


class BodyLookup(Protocol):
    """Structural protocol for celestial bodies participating in frame transforms."""

    @property
    def name(self) -> str:
        """Return the unique identifier of the celestial body."""
        ...

    @property
    def parent_name(self) -> str | None:
        """Return the parent body identifier at the orbital focus, or None for root."""
        ...

    @property
    def elements(self) -> OrbitalElements | None:
        """Return Keplerian orbital elements relative to parent, or None for root."""
        ...


_SUPPORTED_FRAME_SPECS: tuple[tuple[str, str, str], ...] = (
    ("Sun", "Sun", "Heliocentric (Sun-centered) inertial frame"),
    ("Earth", "Earth", "Geocentric (Earth-centered) frame"),
    ("Moon", "Moon", "Selenocentric (Moon-centered) frame"),
    ("Mars", "Mars", "Areocentric (Mars-centered) frame"),
    ("Jupiter", "Jupiter", "Jovicentric (Jupiter-centered) frame"),
    ("Saturn", "Saturn", "Kronocentric (Saturn-centered) frame"),
    ("Uranus", "Uranus", "Uranocentric (Uranus-centered) frame"),
    ("Neptune", "Neptune", "Neptunocentric (Neptune-centered) frame"),
)


def build_frame_registry() -> dict[str, ReferenceFrame]:
    """Construct and return a fresh dictionary of the 8 supported reference frames.

    Returns:
        Ordered mapping from frame name to its ``ReferenceFrame`` descriptor.
    """
    return {
        name: ReferenceFrame(
            name=name,
            center_body_name=center_body_name,
            description=description,
        )
        for name, center_body_name, description in _SUPPORTED_FRAME_SPECS
    }


def local_orbit_offset(body: BodyLookup, jd: float) -> Vec3:
    """Compute the 3D Cartesian offset (in AU) of ``body`` relative to its parent.

    Args:
        body: Celestial body satisfying the ``BodyLookup`` protocol.
        jd: Julian Date epoch of evaluation.

    Returns:
        ``Vec3.ZERO`` when ``body.elements is None``, otherwise the Keplerian
        Cartesian offset vector in AU relative to ``body.parent_name``.
    """
    elements = body.elements
    if elements is None:
        return Vec3.ZERO
    return keplerian_to_cartesian(elements, jd)


def heliocentric_position(
    body_name: str,
    bodies_by_name: Mapping[str, BodyLookup],
    jd: float,
    _cache: dict[str, Vec3] | None = None,
) -> Vec3:
    """Recursively resolve the 3D heliocentric position (in AU) of ``body_name``.

    Args:
        body_name: Name of the target celestial body in ``bodies_by_name``.
        bodies_by_name: Mapping of body names to ``BodyLookup`` descriptors.
        jd: Julian Date epoch of evaluation.
        _cache: Optional memoization dictionary shared across lookups at ``jd``.

    Returns:
        Heliocentric 3D Cartesian position vector in AU.

    Raises:
        KeyError: If ``body_name`` or any ancestor ``parent_name`` is missing.
        ValueError: If a circular ``parent_name`` reference chain is detected.
    """
    cache: dict[str, Vec3] = {} if _cache is None else _cache
    if body_name in cache:
        return cache[body_name]

    visiting: set[str] = set()

    def _resolve(current_name: str) -> Vec3:
        if current_name in cache:
            return cache[current_name]
        if current_name in visiting:
            raise ValueError(
                f"Cycle detected in parent_name chain involving body: {current_name}"
            )
        if current_name not in bodies_by_name:
            raise KeyError(f"Unknown body or parent name: {current_name}")

        body = bodies_by_name[current_name]
        visiting.add(current_name)

        local_vec = local_orbit_offset(body, jd)
        parent_name = body.parent_name
        if parent_name is None:
            helio_vec = local_vec
        else:
            if parent_name == current_name:
                raise ValueError(
                    f"Cycle detected: self-referential parent_name for {current_name}"
                )
            if parent_name not in bodies_by_name:
                raise KeyError(
                    f"Unknown parent_name '{parent_name}' for body '{current_name}'"
                )
            parent_vec = _resolve(parent_name)
            helio_vec = parent_vec + local_vec

        visiting.remove(current_name)
        cache[current_name] = helio_vec
        return helio_vec

    return _resolve(body_name)


def world_position(
    body_name: str,
    frame_center_name: str,
    bodies_by_name: Mapping[str, BodyLookup],
    jd: float,
) -> Vec3:
    """Compute the 3D position (in AU) of ``body_name`` in ``frame_center_name``.

    Args:
        body_name: Name of the target celestial body.
        frame_center_name: Name of the body at the reference frame origin.
        bodies_by_name: Mapping of body names to ``BodyLookup`` descriptors.
        jd: Julian Date epoch of evaluation.

    Returns:
        Relative 3D Cartesian position vector in AU.

    Raises:
        KeyError: If ``body_name``, ``frame_center_name``, or an ancestor is missing.
        ValueError: If a circular ``parent_name`` chain is detected.
    """
    if body_name not in bodies_by_name:
        raise KeyError(f"Unknown body_name: {body_name}")
    if frame_center_name not in bodies_by_name:
        raise KeyError(f"Unknown frame_center_name: {frame_center_name}")

    shared_cache: dict[str, Vec3] = {}
    target_helio_vec = heliocentric_position(
        body_name=body_name,
        bodies_by_name=bodies_by_name,
        jd=jd,
        _cache=shared_cache,
    )
    if body_name == frame_center_name:
        return Vec3.ZERO

    center_helio_vec = heliocentric_position(
        body_name=frame_center_name,
        bodies_by_name=bodies_by_name,
        jd=jd,
        _cache=shared_cache,
    )
    return target_helio_vec - center_helio_vec


def world_positions(
    frame_center_name: str,
    bodies_by_name: Mapping[str, BodyLookup],
    jd: float,
) -> dict[str, Vec3]:
    """Compute 3D positions (in AU) of all bodies relative to ``frame_center_name``.

    Args:
        frame_center_name: Name of the body at the reference frame origin.
        bodies_by_name: Mapping of body names to ``BodyLookup`` descriptors.
        jd: Julian Date epoch of evaluation.

    Returns:
        Dictionary mapping each body name to its relative ``Vec3`` position in AU.

    Raises:
        KeyError: If ``frame_center_name`` or any ancestor is missing.
        ValueError: If a circular ``parent_name`` chain is detected.
    """
    if frame_center_name not in bodies_by_name:
        raise KeyError(f"Unknown frame_center_name: {frame_center_name}")

    shared_cache: dict[str, Vec3] = {}
    center_helio_vec = heliocentric_position(
        body_name=frame_center_name,
        bodies_by_name=bodies_by_name,
        jd=jd,
        _cache=shared_cache,
    )

    result_positions: dict[str, Vec3] = {}
    for name in bodies_by_name:
        body_helio_vec = heliocentric_position(
            body_name=name,
            bodies_by_name=bodies_by_name,
            jd=jd,
            _cache=shared_cache,
        )
        result_positions[name] = body_helio_vec - center_helio_vec

    return result_positions


def body_trajectory_in_frame(
    body_name: str,
    frame_center_name: str,
    bodies_by_name: Mapping[str, BodyLookup],
    start_jd: float,
    span_days: float,
    sample_count: int = 180,
) -> list[Vec3]:
    """Sample a body's 3D trajectory in ``frame_center_name`` over a time span.

    Args:
        body_name: Name of the target celestial body to sample.
        frame_center_name: Name of the body at the reference frame origin.
        bodies_by_name: Mapping of body names to ``BodyLookup`` descriptors.
        start_jd: Starting Julian Date epoch.
        span_days: Positive duration in days across which to sample.
        sample_count: Number of uniformly spaced samples (must be >= 2).

    Returns:
        List of ``sample_count`` ``Vec3`` positions in AU from ``start_jd``
        to ``start_jd + span_days``.

    Raises:
        ValueError: If ``sample_count < 2`` or ``span_days <= 0.0``.
        KeyError: If ``body_name`` or ``frame_center_name`` is missing.
    """
    if sample_count < 2:
        raise ValueError("sample_count must be >= 2.")
    if span_days <= 0.0:
        raise ValueError("span_days must be > 0.0.")
    if body_name not in bodies_by_name:
        raise KeyError(f"Unknown body_name: {body_name}")
    if frame_center_name not in bodies_by_name:
        raise KeyError(f"Unknown frame_center_name: {frame_center_name}")

    step_days = span_days / float(sample_count - 1)
    return [
        world_position(
            body_name=body_name,
            frame_center_name=frame_center_name,
            bodies_by_name=bodies_by_name,
            jd=start_jd + (float(index) * step_days),
        )
        for index in range(sample_count)
    ]