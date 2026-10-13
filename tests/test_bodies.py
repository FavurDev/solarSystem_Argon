"""Headless unit tests for the J2000 solar system body catalog (solar_system.bodies)."""

from __future__ import annotations

import math

import pytest

from solar_system.bodies import (
    AU_IN_KM,
    J2000_EPOCH_JD,
    Body,
    CelestialBody,
    VisualStyle,
    build_named_bodies,
)
from solar_system.kepler import keplerian_to_cartesian, mean_anomaly_at_jd


def test_build_named_bodies_contains_all_25_j2000_bodies() -> None:
    """Verify build_named_bodies() returns all 25 required J2000 solar system bodies."""
    # Arrange
    expected_names = {
        "Sun",
        "Mercury",
        "Venus",
        "Earth",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Moon",
        "Phobos",
        "Deimos",
        "Io",
        "Europa",
        "Ganymede",
        "Callisto",
        "Titan",
        "Triton",
        "Ceres",
        "Vesta",
        "Pallas",
        "Hygiea",
        "1P/Halley",
        "2P/Encke",
        "Hale-Bopp",
    }

    # Act
    bodies = build_named_bodies()
    by_name = {body.name: body for body in bodies}

    # Assert
    assert len(bodies) == 25
    assert set(by_name.keys()) == expected_names
    for body in bodies:
        assert isinstance(body, CelestialBody)
        assert isinstance(body, Body)
        assert isinstance(body.style, VisualStyle)
        assert body.mass_kg > 0.0
        assert body.radius_km > 0.0
        if body.name == "Sun":
            assert body.parent_name is None
            assert body.elements is None
        else:
            assert body.parent_name is not None
            assert body.elements is not None


def test_moons_have_semi_major_axis_converted_from_km_to_au() -> None:
    """Verify all 9 moons have semi-major axes converted from km to AU via AU_IN_KM."""
    # Arrange
    expected_moon_km = {
        "Moon": ("Earth", 384399.0),
        "Phobos": ("Mars", 9376.0),
        "Deimos": ("Mars", 23463.2),
        "Io": ("Jupiter", 421700.0),
        "Europa": ("Jupiter", 671034.0),
        "Ganymede": ("Jupiter", 1070412.0),
        "Callisto": ("Jupiter", 1882709.0),
        "Titan": ("Saturn", 1221870.0),
        "Triton": ("Neptune", 354759.0),
    }

    # Act
    by_name = {body.name: body for body in build_named_bodies()}

    # Assert
    assert AU_IN_KM == pytest.approx(149597870.7, rel=0.0, abs=1e-9)
    for moon_name, (expected_parent, expected_a_km) in expected_moon_km.items():
        moon = by_name[moon_name]
        assert moon.category == "moon"
        assert moon.parent_name == expected_parent
        assert moon.elements is not None
        assert 1e-5 < moon.elements.semi_major_axis_au < 0.02
        assert moon.elements.semi_major_axis_au == pytest.approx(
            expected_a_km / 149597870.7, rel=1e-12
        )


def test_ringed_planets_and_visual_style_properties() -> None:
    """Verify Saturn and Uranus have ring metadata and ring_inner_Mult alias matches."""
    # Arrange / Act
    by_name = {body.name: body for body in build_named_bodies()}
    saturn = by_name["Saturn"]
    uranus = by_name["Uranus"]
    earth = by_name["Earth"]

    # Assert
    assert saturn.style.has_rings is True
    assert saturn.style.ring_inner_mult > 0.0
    assert saturn.style.ring_outer_mult > saturn.style.ring_inner_mult
    assert saturn.style.ring_inner_Mult == saturn.style.ring_inner_mult

    assert uranus.style.has_rings is True
    assert uranus.style.ring_inner_mult > 0.0
    assert uranus.style.ring_outer_mult > uranus.style.ring_inner_mult
    assert uranus.style.ring_inner_Mult == uranus.style.ring_inner_mult

    assert earth.style.has_rings is False
    assert earth.style.ring_inner_Mult == 0.0


def test_triton_retrograde_and_major_moons_prograde_angular_momentum() -> None:
    """Verify Triton's parent-local orbit has negative L_z while prograde moons have positive L_z."""
    # Arrange
    by_name = {body.name: body for body in build_named_bodies()}
    jd0 = J2000_EPOCH_JD
    jd1 = jd0 + 0.5
    prograde_moons = ("Io", "Europa", "Ganymede", "Callisto", "Titan")

    # Act
    triton = by_name["Triton"]
    assert triton.parent_name == "Neptune"
    assert triton.elements is not None
    p0_triton = keplerian_to_cartesian(triton.elements, jd0)
    p1_triton = keplerian_to_cartesian(triton.elements, jd1)
    lz_triton = p0_triton.x * p1_triton.y - p0_triton.y * p1_triton.x

    prograde_lz: dict[str, float] = {}
    for moon_name in prograde_moons:
        moon = by_name[moon_name]
        assert moon.elements is not None
        p0 = keplerian_to_cartesian(moon.elements, jd0)
        p1 = keplerian_to_cartesian(moon.elements, jd1)
        prograde_lz[moon_name] = p0.x * p1.y - p0.y * p1.x

    # Assert
    assert triton.elements.inclination_deg > 90.0
    assert lz_triton < 0.0
    for moon_name, lz_val in prograde_lz.items():
        assert lz_val > 0.0, f"Expected prograde L_z > 0 for {moon_name}, got {lz_val}"


def test_comets_perihelion_and_aphelion_distances_within_1e6_au() -> None:
    """Verify 1P/Halley, 2P/Encke, and Hale-Bopp reach r_p = a(1-e) and r_a = a(1+e) within 1e-6 AU."""
    # Arrange
    by_name = {body.name: body for body in build_named_bodies()}
    comet_names = ("1P/Halley", "2P/Encke", "Hale-Bopp")

    # Act & Assert
    for name in comet_names:
        comet = by_name[name]
        assert comet.category == "comet"
        assert comet.elements is not None
        elem = comet.elements

        # Signed orbital_period_days ensures mean_anomaly_at_jd reaches M=0 at jd_perihelion
        # and M=pi at jd_aphelion even for retrograde 1P/Halley (orbital_period_days < 0).
        jd_perihelion = (
            elem.epoch_jd - (elem.mean_anomaly_epoch_deg / 360.0) * elem.orbital_period_days
        )
        jd_aphelion = (
            elem.epoch_jd
            + ((180.0 - elem.mean_anomaly_epoch_deg) / 360.0) * elem.orbital_period_days
        )

        m_peri = mean_anomaly_at_jd(elem, jd_perihelion)
        m_aph = mean_anomaly_at_jd(elem, jd_aphelion)
        r_peri = keplerian_to_cartesian(elem, jd_perihelion).norm()
        r_aph = keplerian_to_cartesian(elem, jd_aphelion).norm()

        expected_rp = elem.semi_major_axis_au * (1.0 - elem.eccentricity)
        expected_ra = elem.semi_major_axis_au * (1.0 + elem.eccentricity)

        assert m_peri == pytest.approx(0.0, abs=1e-12) or m_peri == pytest.approx(
            math.tau, abs=1e-12
        )
        assert m_aph == pytest.approx(math.pi, abs=1e-12)
        assert abs(r_peri - expected_rp) < 1e-6
        assert abs(r_aph - expected_ra) < 1e-6
