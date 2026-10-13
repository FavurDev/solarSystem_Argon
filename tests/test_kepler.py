"""Unit tests for OrbitalElements and the analytical Keplerian solver (`solar_system.kepler`)."""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pytest
from solar_system.kepler import (
    GAUSSIAN_GRAVITATIONAL_CONSTANT,
    J2000_JD,
    OrbitalElements,
    keplerian_to_cartesian,
    mean_anomaly_at_jd,
    normalize_radians,
    orbital_period_days,
    solve_kepler,
    true_anomaly_from_eccentric,
)


def test_kepler_constants_and_orbital_elements_validation() -> None:
    """Verify J2000_JD, GAUSSIAN_GRAVITATIONAL_CONSTANT, and OrbitalElements validation."""
    # Arrange
    prograde = OrbitalElements(
        semi_major_axis_au=1.0,
        eccentricity=0.0167,
        inclination_deg=0.0,
        lon_ascending_node_deg=0.0,
        arg_periapsis_deg=102.9,
        mean_anomaly_epoch_deg=100.5,
        orbital_period_days=365.256,
    )
    retrograde = OrbitalElements(
        semi_major_axis_au=17.834,
        eccentricity=0.96714,
        inclination_deg=162.26,
        lon_ascending_node_deg=58.42,
        arg_periapsis_deg=111.33,
        mean_anomaly_epoch_deg=38.38,
        orbital_period_days=-27509.7,
    )

    # Act & Assert
    assert J2000_JD == 2451545.0
    assert GAUSSIAN_GRAVITATIONAL_CONSTANT == pytest.approx(0.01720209895, abs=1e-15)
    assert prograde.epoch_jd == J2000_JD
    assert retrograde.orbital_period_days < 0.0
    assert not hasattr(prograde, "__dict__")
    with pytest.raises(FrozenInstanceError):
        prograde.semi_major_axis_au = 2.0  # type: ignore[misc]

    for invalid_a in (0.0, -1.5):
        with pytest.raises(ValueError, match="semi_major_axis_au"):
            OrbitalElements(
                semi_major_axis_au=invalid_a,
                eccentricity=0.1,
                inclination_deg=0.0,
                lon_ascending_node_deg=0.0,
                arg_periapsis_deg=0.0,
                mean_anomaly_epoch_deg=0.0,
                orbital_period_days=100.0,
            )

    for invalid_e in (-0.01, 1.0, 1.25):
        with pytest.raises(ValueError, match="eccentricity"):
            OrbitalElements(
                semi_major_axis_au=1.0,
                eccentricity=invalid_e,
                inclination_deg=0.0,
                lon_ascending_node_deg=0.0,
                arg_periapsis_deg=0.0,
                mean_anomaly_epoch_deg=0.0,
                orbital_period_days=100.0,
            )

    with pytest.raises(ValueError, match="orbital_period_days"):
        OrbitalElements(
            semi_major_axis_au=1.0,
            eccentricity=0.1,
            inclination_deg=0.0,
            lon_ascending_node_deg=0.0,
            arg_periapsis_deg=0.0,
            mean_anomaly_epoch_deg=0.0,
            orbital_period_days=0.0,
        )


def test_normalize_radians_wrapping() -> None:
    """Verify normalize_radians wraps negative, zero, 2*pi, and multi-turn angles into [0, 2*pi)."""
    # Arrange
    cases = [
        (0.0, 0.0),
        (math.pi, math.pi),
        (math.tau, 0.0),
        (-math.pi / 2.0, 1.5 * math.pi),
        (-4.0 * math.pi, 0.0),
        (7.0 * math.pi, math.pi),
        (-1e-17, 0.0),
    ]

    # Act & Assert
    for raw_angle, expected in cases:
        wrapped = normalize_radians(raw_angle)
        assert 0.0 <= wrapped < math.tau
        assert wrapped == pytest.approx(expected, abs=1e-12)


def test_solve_kepler_convergence_across_eccentricity_grid() -> None:
    """Verify solve_kepler converges to < 1e-12 residual in <= 50 iterations across e and M."""
    # Arrange
    eccentricities = [0.0, 0.0167, 0.2056, 0.5, 0.847, 0.96714, 0.995086]
    mean_anomalies = [
        0.0,
        1e-6,
        1e-4,
        0.01,
        0.1,
        math.pi / 6.0,
        math.pi / 4.0,
        math.pi / 2.0,
        math.pi - 1e-4,
        math.pi,
        math.pi + 1e-4,
        1.5 * math.pi,
        math.tau - 0.01,
        math.tau - 1e-6,
    ]

    # Act & Assert
    for ecc in eccentricities:
        for mean_anom in mean_anomalies:
            ecc_anom, iterations = solve_kepler(
                mean_anomaly_rad=mean_anom,
                eccentricity=ecc,
                tolerance=1e-12,
                max_iter=60,
            )
            m_norm = normalize_radians(mean_anom)
            residual = abs(ecc_anom - (ecc * math.sin(ecc_anom)) - m_norm)
            assert residual < 1e-12
            assert iterations <= 50
            if ecc == 0.0:
                assert ecc_anom == pytest.approx(m_norm, abs=1e-12)


def test_solve_kepler_invalid_arguments() -> None:
    """Verify solve_kepler raises ValueError on invalid eccentricity, tolerance, or max_iter."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="eccentricity"):
        solve_kepler(1.0, -0.1)
    with pytest.raises(ValueError, match="eccentricity"):
        solve_kepler(1.0, 1.0)
    with pytest.raises(ValueError, match="tolerance"):
        solve_kepler(1.0, 0.5, tolerance=0.0)
    with pytest.raises(ValueError, match="tolerance"):
        solve_kepler(1.0, 0.5, tolerance=-1e-9)
    with pytest.raises(ValueError, match="max_iter"):
        solve_kepler(1.0, 0.5, max_iter=0)


def test_true_anomaly_from_eccentric_cardinal_and_conic_relation() -> None:
    """Verify true_anomaly_from_eccentric at cardinal points, conic identity, and validation."""
    # Arrange
    ecc = 0.5
    ecc_anomalies = [0.0, math.pi / 3.0, math.pi / 2.0, math.pi, 1.5 * math.pi]

    # Act
    nu_zero = true_anomaly_from_eccentric(0.0, ecc)
    nu_pi = true_anomaly_from_eccentric(math.pi, ecc)

    # Assert
    assert nu_zero == pytest.approx(0.0, abs=1e-12)
    assert nu_pi == pytest.approx(math.pi, abs=1e-12)
    for ecc_anom in ecc_anomalies:
        nu = true_anomaly_from_eccentric(ecc_anom, ecc)
        expected_cos_nu = (math.cos(ecc_anom) - ecc) / (1.0 - (ecc * math.cos(ecc_anom)))
        assert math.cos(nu) == pytest.approx(expected_cos_nu, abs=1e-12)

    with pytest.raises(ValueError, match="eccentricity"):
        true_anomaly_from_eccentric(0.5, -0.05)
    with pytest.raises(ValueError, match="eccentricity"):
        true_anomaly_from_eccentric(0.5, 1.0)


def test_earth_j2000_keplerian_to_cartesian_and_conic_identity() -> None:
    """Verify Earth J2000 heliocentric position radius ~1.0 AU and exact conic radius identity."""
    # Arrange
    earth_elements = OrbitalElements(
        semi_major_axis_au=1.00000261,
        eccentricity=0.01671123,
        inclination_deg=0.00005,
        lon_ascending_node_deg=-11.26064,
        arg_periapsis_deg=114.20783,
        mean_anomaly_epoch_deg=357.51716,
        orbital_period_days=365.256363,
        epoch_jd=J2000_JD,
    )

    # Act
    pos = keplerian_to_cartesian(earth_elements, J2000_JD)
    m_rad = mean_anomaly_at_jd(earth_elements, J2000_JD)
    e_rad, _ = solve_kepler(m_rad, earth_elements.eccentricity)
    expected_r = earth_elements.semi_major_axis_au * (
        1.0 - (earth_elements.eccentricity * math.cos(e_rad))
    )

    # Assert
    assert abs(pos.norm() - 1.0) <= 0.02
    assert abs(pos.norm() - expected_r) < 1e-10


def test_inclined_orbit_produces_nonzero_z_and_periodicity() -> None:
    """Verify inclined orbit (i > 0) produces non-zero z out of ecliptic plane and repeats after T."""
    # Arrange
    inclined_elements = OrbitalElements(
        semi_major_axis_au=2.0,
        eccentricity=0.1,
        inclination_deg=30.0,
        lon_ascending_node_deg=20.0,
        arg_periapsis_deg=45.0,
        mean_anomaly_epoch_deg=45.0,
        orbital_period_days=1000.0,
        epoch_jd=J2000_JD,
    )

    # Act
    pos0 = keplerian_to_cartesian(inclined_elements, J2000_JD)
    pos1 = keplerian_to_cartesian(
        inclined_elements,
        J2000_JD + inclined_elements.orbital_period_days,
    )

    # Assert
    assert abs(pos0.z) > 0.1
    assert (pos1 - pos0).norm() < 1e-12


def test_retrograde_orbit_mean_anomaly_and_angular_momentum_direction() -> None:
    """Verify retrograde orbit (T < 0, i > 90) decreases M(jd) and preserves L_z < 0."""
    # Arrange
    retrograde_elements = OrbitalElements(
        semi_major_axis_au=17.834,
        eccentricity=0.96714,
        inclination_deg=162.26,
        lon_ascending_node_deg=58.42,
        arg_periapsis_deg=111.33,
        mean_anomaly_epoch_deg=180.0,
        orbital_period_days=-27509.7,
        epoch_jd=J2000_JD,
    )

    # Act
    m0 = mean_anomaly_at_jd(retrograde_elements, J2000_JD)
    m1 = mean_anomaly_at_jd(retrograde_elements, J2000_JD + 100.0)
    p0 = keplerian_to_cartesian(retrograde_elements, J2000_JD)
    p1 = keplerian_to_cartesian(retrograde_elements, J2000_JD + 10.0)
    cross_z = (p0.x * p1.y) - (p0.y * p1.x)

    # Assert
    assert m1 < m0
    assert cross_z < 0.0


def test_orbital_period_days_kepler_third_law() -> None:
    """Verify orbital_period_days matches Kepler's third law and validates positive inputs."""
    # Arrange
    semi_major_axis_au = 1.0
    central_mass_solar = 1.0

    # Act
    earth_period = orbital_period_days(semi_major_axis_au, central_mass_solar)

    # Assert
    assert abs(earth_period - 365.2568983) < 0.01
    with pytest.raises(ValueError, match="semi_major_axis_au"):
        orbital_period_days(0.0, 1.0)
    with pytest.raises(ValueError, match="semi_major_axis_au"):
        orbital_period_days(-2.0, 1.0)
    with pytest.raises(ValueError, match="central_mass_solar"):
        orbital_period_days(1.0, 0.0)
    with pytest.raises(ValueError, match="central_mass_solar"):
        orbital_period_days(1.0, -1.0)