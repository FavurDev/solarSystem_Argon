"""Unit tests for reference frames and parent-chain transformations (`solar_system.frames`)."""

from __future__ import annotations

import math
import sys
from dataclasses import FrozenInstanceError, dataclass

import pytest

from solar_system.frames import (
    BodyLookup,
    ReferenceFrame,
    body_trajectory_in_frame,
    build_frame_registry,
    heliocentric_position,
    local_orbit_offset,
    world_position,
    world_positions,
)
from solar_system.kepler import J2000_JD, OrbitalElements, keplerian_to_cartesian
from solar_system.vector import Vec3


@dataclass(frozen=True, slots=True)
class _TestBody:
    """Lightweight test double satisfying the BodyLookup structural protocol."""

    name: str
    parent_name: str | None
    elements: OrbitalElements | None


def _build_test_catalog() -> dict[str, _TestBody]:
    """Build a self-contained test catalog with realistic J2000 orbital elements."""
    return {
        "Sun": _TestBody(name="Sun", parent_name=None, elements=None),
        "Earth": _TestBody(
            name="Earth",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=1.00000261,
                eccentricity=0.01671123,
                inclination_deg=0.00005,
                lon_ascending_node_deg=-11.26064,
                arg_periapsis_deg=114.20783,
                mean_anomaly_epoch_deg=357.51716,
                orbital_period_days=365.256363,
            ),
        ),
        "Moon": _TestBody(
            name="Moon",
            parent_name="Earth",
            elements=OrbitalElements(
                semi_major_axis_au=0.00256955,
                eccentricity=0.0549,
                inclination_deg=5.145,
                lon_ascending_node_deg=125.08,
                arg_periapsis_deg=318.15,
                mean_anomaly_epoch_deg=135.27,
                orbital_period_days=27.321661,
            ),
        ),
        "Mars": _TestBody(
            name="Mars",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=1.52366231,
                eccentricity=0.09341233,
                inclination_deg=1.85061,
                lon_ascending_node_deg=49.57854,
                arg_periapsis_deg=286.502,
                mean_anomaly_epoch_deg=19.373,
                orbital_period_days=686.97959,
            ),
        ),
        "Jupiter": _TestBody(
            name="Jupiter",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=5.20336301,
                eccentricity=0.04839266,
                inclination_deg=1.30530,
                lon_ascending_node_deg=100.55615,
                arg_periapsis_deg=-85.8023,
                mean_anomaly_epoch_deg=19.65053,
                orbital_period_days=4332.589,
            ),
        ),
        "Saturn": _TestBody(
            name="Saturn",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=9.53707032,
                eccentricity=0.05415060,
                inclination_deg=2.48446,
                lon_ascending_node_deg=113.71504,
                arg_periapsis_deg=-21.2831,
                mean_anomaly_epoch_deg=317.020,
                orbital_period_days=10759.22,
            ),
        ),
        "Uranus": _TestBody(
            name="Uranus",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=19.19126393,
                eccentricity=0.04716771,
                inclination_deg=0.76986,
                lon_ascending_node_deg=74.22988,
                arg_periapsis_deg=96.73436,
                mean_anomaly_epoch_deg=142.2386,
                orbital_period_days=30685.4,
            ),
        ),
        "Neptune": _TestBody(
            name="Neptune",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=30.06896348,
                eccentricity=0.00858587,
                inclination_deg=1.76917,
                lon_ascending_node_deg=131.72169,
                arg_periapsis_deg=-86.75034,
                mean_anomaly_epoch_deg=256.228,
                orbital_period_days=60189.0,
            ),
        ),
        "Io": _TestBody(
            name="Io",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=0.002819,
                eccentricity=0.0041,
                inclination_deg=0.05,
                lon_ascending_node_deg=43.977,
                arg_periapsis_deg=84.129,
                mean_anomaly_epoch_deg=342.021,
                orbital_period_days=1.769138,
            ),
        ),
        "Europa": _TestBody(
            name="Europa",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=0.004486,
                eccentricity=0.009,
                inclination_deg=0.47,
                lon_ascending_node_deg=219.106,
                arg_periapsis_deg=88.97,
                mean_anomaly_epoch_deg=171.016,
                orbital_period_days=3.551181,
            ),
        ),
        "Ganymede": _TestBody(
            name="Ganymede",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=0.007155,
                eccentricity=0.0013,
                inclination_deg=0.20,
                lon_ascending_node_deg=63.552,
                arg_periapsis_deg=192.417,
                mean_anomaly_epoch_deg=317.54,
                orbital_period_days=7.154553,
            ),
        ),
        "Callisto": _TestBody(
            name="Callisto",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=0.012585,
                eccentricity=0.0074,
                inclination_deg=0.19,
                lon_ascending_node_deg=298.848,
                arg_periapsis_deg=52.643,
                mean_anomaly_epoch_deg=181.408,
                orbital_period_days=16.689018,
            ),
        ),
    }


def test_reference_frame_and_registry_contracts() -> None:
    """Verify ReferenceFrame validation, immutability, and 8-frame registry contents."""
    # Arrange
    expected_keys = (
        "Sun",
        "Earth",
        "Moon",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
    )

    # Act
    registry = build_frame_registry()
    second_registry = build_frame_registry()

    # Assert
    assert tuple(registry.keys()) == expected_keys
    assert registry == second_registry
    assert registry is not second_registry
    for key, frame in registry.items():
        assert isinstance(frame, ReferenceFrame)
        assert frame.name == key
        assert frame.center_body_name == key
        assert frame.description != ""
        assert not hasattr(frame, "__dict__")

    earth_frame = registry["Earth"]
    with pytest.raises(FrozenInstanceError):
        earth_frame.name = "Mutated"  # type: ignore[misc]

    for invalid_name in ("", "   "):
        with pytest.raises(ValueError, match="name"):
            ReferenceFrame(
                name=invalid_name,
                center_body_name="Sun",
                description="Invalid name",
            )
        with pytest.raises(ValueError, match="center_body_name"):
            ReferenceFrame(
                name="Valid",
                center_body_name=invalid_name,
                description="Invalid center",
            )


def test_local_orbit_offset_and_sun_root() -> None:
    """Verify local_orbit_offset returns Vec3.ZERO for Sun and Keplerian vector for planets."""
    # Arrange
    catalog = _build_test_catalog()
    sun_lookup: BodyLookup = catalog["Sun"]
    earth_lookup: BodyLookup = catalog["Earth"]
    jd = J2000_JD + 45.25

    # Act
    sun_offset = local_orbit_offset(sun_lookup, jd)
    earth_offset = local_orbit_offset(earth_lookup, jd)
    sun_helio = heliocentric_position("Sun", catalog, jd)

    # Assert
    assert sun_offset == Vec3.ZERO
    assert sun_helio == Vec3.ZERO
    assert earth_lookup.elements is not None
    expected_earth = keplerian_to_cartesian(earth_lookup.elements, jd)
    assert (earth_offset - expected_earth).norm() < 1e-12


def test_origin_invariance_and_antisymmetry_across_all_frames() -> None:
    """Verify origin invariance ||world_position(F, F)|| < 1e-12 and antisymmetry across epochs."""
    # Arrange
    catalog = _build_test_catalog()
    registry = build_frame_registry()
    epochs = (J2000_JD, J2000_JD + 12.5, J2000_JD + 180.0)

    # Act & Assert
    for jd in epochs:
        for frame_name in registry:
            origin_pos = world_position(frame_name, frame_name, catalog, jd)
            assert origin_pos.norm() < 1e-12

        earth_in_sun = world_position("Earth", "Sun", catalog, jd)
        sun_in_earth = world_position("Sun", "Earth", catalog, jd)
        assert (earth_in_sun + sun_in_earth).norm() < 1e-12

        moon_in_earth = world_position("Moon", "Earth", catalog, jd)
        earth_in_moon = world_position("Earth", "Moon", catalog, jd)
        assert (moon_in_earth + earth_in_moon).norm() < 1e-12


def test_moon_heliocentric_parent_chain_across_lunar_month() -> None:
    """Verify Moon heliocentric position composes Earth + local Moon offset across 30 days."""
    # Arrange
    catalog = _build_test_catalog()
    expected_semi_major_au = 0.00256955
    tolerance_au = 0.0002

    # Act & Assert
    for day_offset in range(31):
        jd = J2000_JD + float(day_offset)
        moon_sun = world_position("Moon", "Sun", catalog, jd)
        earth_sun = world_position("Earth", "Sun", catalog, jd)
        moon_earth = world_position("Moon", "Earth", catalog, jd)

        relative_from_helio = moon_sun - earth_sun
        distance_au = relative_from_helio.norm()

        assert abs(distance_au - expected_semi_major_au) <= tolerance_au
        assert (relative_from_helio - moon_earth).norm() < 1e-12


def test_galilean_moons_bounded_in_jupiter_frame() -> None:
    """Verify Galilean moons stay within < 0.02 AU of Jupiter in the Jupiter frame over 30 days."""
    # Arrange
    catalog = _build_test_catalog()
    galilean_moons = ("Io", "Europa", "Ganymede", "Callisto")

    # Act & Assert
    for day_offset in range(0, 31, 2):
        jd = J2000_JD + float(day_offset)
        positions_jup = world_positions("Jupiter", catalog, jd)
        assert positions_jup["Jupiter"].norm() < 1e-12

        for moon_name in galilean_moons:
            moon_pos_batch = positions_jup[moon_name]
            moon_pos_single = world_position(moon_name, "Jupiter", catalog, jd)
            assert (moon_pos_batch - moon_pos_single).norm() < 1e-12
            assert 0.001 < moon_pos_batch.norm() < 0.02


def test_mars_geocentric_retrograde_reversal() -> None:
    """Verify Mars exhibits apparent geocentric retrograde motion over a 780-day synodic span."""
    # Arrange
    catalog = _build_test_catalog()
    start_jd = J2000_JD
    span_days = 780.0
    sample_count = 390

    # Act
    trajectory = body_trajectory_in_frame(
        body_name="Mars",
        frame_center_name="Earth",
        bodies_by_name=catalog,
        start_jd=start_jd,
        span_days=span_days,
        sample_count=sample_count,
    )

    # Assert
    assert len(trajectory) == sample_count
    longitudes = [math.atan2(point.y, point.x) for point in trajectory]
    deltas: list[float] = []
    for idx in range(len(longitudes) - 1):
        delta = longitudes[idx + 1] - longitudes[idx]
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta <= -math.pi:
            delta += 2.0 * math.pi
        deltas.append(delta)

    assert max(deltas) > 0.0
    assert min(deltas) < 0.0
    retrograde_steps = sum(1 for delta in deltas if delta < 0.0)
    assert retrograde_steps >= 15


def test_heliocentric_position_cache_reuse_and_world_positions() -> None:
    """Verify _cache memoization in heliocentric_position and full-catalog world_positions."""
    # Arrange
    catalog = _build_test_catalog()
    jd = J2000_JD + 90.0
    cache: dict[str, Vec3] = {}

    # Act
    io_helio = heliocentric_position("Io", catalog, jd, _cache=cache)
    jupiter_cached = cache["Jupiter"]
    jupiter_direct = heliocentric_position("Jupiter", catalog, jd, _cache=cache)
    all_in_earth = world_positions("Earth", catalog, jd)

    # Assert
    assert set(cache.keys()) >= {"Io", "Jupiter", "Sun"}
    assert cache["Sun"] == Vec3.ZERO
    assert cache["Io"] == io_helio
    assert jupiter_direct == jupiter_cached
    assert set(all_in_earth.keys()) == set(catalog.keys())
    assert all_in_earth["Earth"].norm() < 1e-12
    for body_name, pos in all_in_earth.items():
        expected = world_position(body_name, "Earth", catalog, jd)
        assert (pos - expected).norm() < 1e-12


def test_cycle_detection_and_unknown_body_errors() -> None:
    """Verify ValueError on parent-chain cycles and KeyError on unknown body or frame names."""
    # Arrange
    catalog = _build_test_catalog()
    earth_elements = catalog["Earth"].elements
    self_cycle_catalog = {
        "SelfBody": _TestBody(
            name="SelfBody",
            parent_name="SelfBody",
            elements=earth_elements,
        ),
    }
    two_node_cycle_catalog = {
        "Alpha": _TestBody(name="Alpha", parent_name="Beta", elements=earth_elements),
        "Beta": _TestBody(name="Beta", parent_name="Alpha", elements=earth_elements),
    }
    broken_parent_catalog = {
        "Orphan": _TestBody(
            name="Orphan",
            parent_name="MissingParent",
            elements=earth_elements,
        ),
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Cycle"):
        heliocentric_position("SelfBody", self_cycle_catalog, J2000_JD)

    with pytest.raises(ValueError, match="Cycle"):
        heliocentric_position("Alpha", two_node_cycle_catalog, J2000_JD)

    with pytest.raises(KeyError):
        heliocentric_position("UnknownBody", catalog, J2000_JD)

    with pytest.raises(KeyError):
        heliocentric_position("Orphan", broken_parent_catalog, J2000_JD)

    with pytest.raises(KeyError):
        world_position("UnknownBody", "Sun", catalog, J2000_JD)

    with pytest.raises(KeyError):
        world_position("Earth", "UnknownCenter", catalog, J2000_JD)

    with pytest.raises(KeyError):
        world_positions("UnknownCenter", catalog, J2000_JD)


def test_body_trajectory_in_frame_validation() -> None:
    """Verify body_trajectory_in_frame input guards, endpoints, and headless isolation."""
    # Arrange
    catalog = _build_test_catalog()
    start_jd = J2000_JD
    span_days = 100.0

    # Act
    points = body_trajectory_in_frame(
        body_name="Earth",
        frame_center_name="Sun",
        bodies_by_name=catalog,
        start_jd=start_jd,
        span_days=span_days,
        sample_count=5,
    )

    # Assert
    assert len(points) == 5
    expected_start = world_position("Earth", "Sun", catalog, start_jd)
    expected_end = world_position("Earth", "Sun", catalog, start_jd + span_days)
    assert (points[0] - expected_start).norm() < 1e-12
    assert (points[-1] - expected_end).norm() < 1e-12
    assert "pygame" not in sys.modules

    for invalid_samples in (1, 0, -3):
        with pytest.raises(ValueError, match="sample_count"):
            body_trajectory_in_frame(
                body_name="Earth",
                frame_center_name="Sun",
                bodies_by_name=catalog,
                start_jd=start_jd,
                span_days=span_days,
                sample_count=invalid_samples,
            )

    for invalid_span in (0.0, -10.0):
        with pytest.raises(ValueError, match="span_days"):
            body_trajectory_in_frame(
                body_name="Earth",
                frame_center_name="Sun",
                bodies_by_name=catalog,
                start_jd=start_jd,
                span_days=invalid_span,
                sample_count=10,
            )

    with pytest.raises(KeyError):
        body_trajectory_in_frame(
            body_name="UnknownBody",
            frame_center_name="Sun",
            bodies_by_name=catalog,
            start_jd=start_jd,
            span_days=span_days,
            sample_count=10,
        )

    with pytest.raises(KeyError):
        body_trajectory_in_frame(
            body_name="Earth",
            frame_center_name="UnknownCenter",
            bodies_by_name=catalog,
            start_jd=start_jd,
            span_days=span_days,
            sample_count=10,
        )
