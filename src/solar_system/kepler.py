"""Analytical Keplerian orbital elements and safeguarded Newton-Raphson solver.

Provides the ``OrbitalElements`` frozen slotted dataclass, reference constants
``J2000_JD`` and ``GAUSSIAN_GRAVITATIONAL_CONSTANT``, angle normalization,
mean anomaly propagation, a safeguarded Newton-Raphson solver for Kepler's
equation ``M = E - e * sin(E)`` with bisection fallback, true anomaly
conversion, 3D perifocal-to-ecliptic coordinate transformation, and Kepler's
Third Law orbital period calculation.
"""

# CHANGELOG:
# - Sprint 1: Created OrbitalElements and safeguarded 3D Keplerian orbital solver.

from __future__ import annotations

import math
from dataclasses import dataclass

from solar_system.vector import Vec3

J2000_JD: float = 2451545.0
GAUSSIAN_GRAVITATIONAL_CONSTANT: float = 0.01720209895


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """Classical Keplerian orbital elements referenced to a Julian Date epoch.

    Attributes:
        semi_major_axis_au: Semi-major axis ``a`` in Astronomical Units (> 0.0).
        eccentricity: Dimensionless orbital eccentricity ``e`` in ``[0.0, 1.0)``.
        inclination_deg: Orbital inclination ``i`` in degrees relative to the reference plane.
        lon_ascending_node_deg: Longitude of the ascending node ``Omega`` in degrees.
        arg_periapsis_deg: Argument of periapsis ``omega`` in degrees.
        mean_anomaly_epoch_deg: Mean anomaly ``M0`` at ``epoch_jd`` in degrees.
        orbital_period_days: Sidereal orbital period ``T`` in days (negative for retrograde).
        epoch_jd: Reference Julian Date epoch (default ``J2000_JD = 2451545.0``).
    """

    semi_major_axis_au: float
    eccentricity: float
    inclination_deg: float
    lon_ascending_node_deg: float
    arg_periapsis_deg: float
    mean_anomaly_epoch_deg: float
    orbital_period_days: float
    epoch_jd: float = J2000_JD

    def __post_init__(self) -> None:
        """Validate physical domain invariants for closed elliptical orbits.

        Raises:
            ValueError: If ``semi_major_axis_au <= 0.0``, ``eccentricity`` is outside
                ``[0.0, 1.0)``, or ``orbital_period_days == 0.0``.
        """
        if self.semi_major_axis_au <= 0.0:
            raise ValueError("semi_major_axis_au must be > 0.0")
        if not (0.0 <= self.eccentricity < 1.0):
            raise ValueError("eccentricity must satisfy 0.0 <= eccentricity < 1.0")
        if self.orbital_period_days == 0.0:
            raise ValueError("orbital_period_days must be non-zero")


def normalize_radians(angle_rad: float) -> float:
    """Wrap an angle in radians into the half-open interval ``[0.0, 2*pi)``.

    Args:
        angle_rad: Input angle in radians.

    Returns:
        Equivalent angle wrapped into ``[0.0, math.tau)``.
    """
    wrapped_angle = angle_rad % math.tau
    if wrapped_angle < 0.0 or wrapped_angle >= math.tau:
        wrapped_angle = wrapped_angle % math.tau
        if wrapped_angle >= math.tau:
            wrapped_angle = 0.0
    return wrapped_angle


def mean_anomaly_at_jd(elements: OrbitalElements, jd: float) -> float:
    """Compute the normalized mean anomaly ``M(jd)`` in ``[0.0, 2*pi)`` at Julian Date ``jd``.

    Args:
        elements: Validated Keplerian ``OrbitalElements`` for the orbiting body.
        jd: Target Julian Date at which to evaluate the mean anomaly.

    Returns:
        Normalized mean anomaly in radians within ``[0.0, math.tau)``.
    """
    m0_rad = math.radians(elements.mean_anomaly_epoch_deg)
    elapsed_days = jd - elements.epoch_jd
    mean_motion_rad_per_day = math.tau / elements.orbital_period_days
    raw_mean_anomaly = m0_rad + (mean_motion_rad_per_day * elapsed_days)
    return normalize_radians(raw_mean_anomaly)


def solve_kepler(
    mean_anomaly_rad: float,
    eccentricity: float,
    tolerance: float = 1e-12,
    max_iter: int = 60,
) -> tuple[float, int]:
    """Solve Kepler's equation ``M = E - e * sin(E)`` via safeguarded Newton-Raphson.

    # IMPLEMENTATION DECISION: Use piecewise initial guess (E0 = M_norm for e < 0.8,
    # E0 = pi for e >= 0.8) combined with a dynamically tightened bracket [low, high]
    # on [0.0, 2*pi] and bisection fallback whenever a Newton candidate exits (low, high).
    # Rationale: Near periapsis (M -> 0) for near-parabolic comets (e = 0.995086),
    # f'(E) = 1 - e*cos(E) is very small and unguarded Newton steps can overshoot.
    # Alternatives: Fixed-point iteration (too slow for high e) or Halley's method.

    Args:
        mean_anomaly_rad: Mean anomaly ``M`` in radians.
        eccentricity: Orbital eccentricity ``e`` in ``[0.0, 1.0)``.
        tolerance: Absolute residual convergence threshold (default ``1e-12``).
        max_iter: Maximum solver iterations allowed (default ``60``).

    Returns:
        Tuple ``(eccentric_anomaly_rad, iterations_used)``.

    Raises:
        ValueError: If ``eccentricity`` is outside ``[0.0, 1.0)``, ``tolerance <= 0.0``,
            or ``max_iter < 1``.
    """
    if not (0.0 <= eccentricity < 1.0):
        raise ValueError("eccentricity must satisfy 0.0 <= eccentricity < 1.0")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be > 0.0")
    if max_iter < 1:
        raise ValueError("max_iter must be >= 1")

    m_norm = normalize_radians(mean_anomaly_rad)
    if eccentricity == 0.0 or m_norm == 0.0:
        return (m_norm, 0)

    ecc_anom = m_norm if eccentricity < 0.8 else math.pi
    low = 0.0
    high = math.tau

    for iteration in range(1, max_iter + 1):
        f_val = ecc_anom - (eccentricity * math.sin(ecc_anom)) - m_norm
        if abs(f_val) < tolerance:
            return (ecc_anom, iteration)

        if f_val < 0.0:
            low = max(low, ecc_anom)
        else:
            high = min(high, ecc_anom)

        f_prime = 1.0 - (eccentricity * math.cos(ecc_anom))
        if abs(f_prime) < 1e-15:
            e_next = 0.5 * (low + high)
        else:
            delta = f_val / f_prime
            e_candidate = ecc_anom - delta
            if e_candidate <= low or e_candidate >= high:
                e_next = 0.5 * (low + high)
            else:
                e_next = e_candidate

        ecc_anom = e_next
        post_step_residual = abs(ecc_anom - (eccentricity * math.sin(ecc_anom)) - m_norm)
        if post_step_residual < tolerance:
            return (ecc_anom, iteration)

    return (ecc_anom, max_iter)


def true_anomaly_from_eccentric(
    eccentric_anomaly_rad: float,
    eccentricity: float,
) -> float:
    """Convert eccentric anomaly ``E`` (radians) to true anomaly ``nu`` (radians).

    Args:
        eccentric_anomaly_rad: Eccentric anomaly ``E`` in radians.
        eccentricity: Orbital eccentricity ``e`` in ``[0.0, 1.0)``.

    Returns:
        True anomaly ``nu`` in radians computed via half-angle ``atan2``.

    Raises:
        ValueError: If ``eccentricity`` is outside ``[0.0, 1.0)``.
    """
    if not (0.0 <= eccentricity < 1.0):
        raise ValueError("eccentricity must satisfy 0.0 <= eccentricity < 1.0")
    half_e = 0.5 * eccentric_anomaly_rad
    y_term = math.sqrt(1.0 + eccentricity) * math.sin(half_e)
    x_term = math.sqrt(1.0 - eccentricity) * math.cos(half_e)
    half_nu = math.atan2(y_term, x_term)
    return 2.0 * half_nu


def keplerian_to_cartesian(elements: OrbitalElements, jd: float) -> Vec3:
    """Transform Keplerian orbital elements at Julian Date ``jd`` to 3D Cartesian AU.

    # IMPLEMENTATION DECISION: When orbital_period_days < 0.0 and inclination_deg > 90.0,
    # compute effective_inc_deg = 180.0 - elements.inclination_deg before rotate_x.
    # Rationale: Retrograde catalog bodies (Triton, 1P/Halley) encode retrograde motion
    # via both negative orbital_period_days (reversing motion in the perifocal plane)
    # and IAU inclination > 90 deg; applying rotate_x with > 90 deg on top of reversed
    # perifocal motion would invert L_z a second time. Using 180 - inclination_deg
    # applies the exact acute plane tilt while preserving retrograde L_z < 0.
    # Alternatives: Using positive period with i > 90 deg (breaks M(jd) decrease contract).

    Args:
        elements: Validated ``OrbitalElements`` of the orbiting body.
        jd: Target Julian Date at which to compute the 3D position.

    Returns:
        ``Vec3`` position in Astronomical Units relative to the reference primary.
    """
    m_rad = mean_anomaly_at_jd(elements, jd)
    e_rad, _ = solve_kepler(m_rad, elements.eccentricity)
    x_perifocal = elements.semi_major_axis_au * (math.cos(e_rad) - elements.eccentricity)
    y_perifocal = (
        elements.semi_major_axis_au
        * math.sqrt(1.0 - (elements.eccentricity * elements.eccentricity))
        * math.sin(e_rad)
    )
    pos_perifocal = Vec3(x=x_perifocal, y=y_perifocal, z=0.0)

    arg_periapsis_rad = math.radians(elements.arg_periapsis_deg)
    if elements.orbital_period_days < 0.0 and elements.inclination_deg > 90.0:
        effective_inc_deg = 180.0 - elements.inclination_deg
    else:
        effective_inc_deg = elements.inclination_deg
    inc_rad = math.radians(effective_inc_deg)
    lon_ascending_node_rad = math.radians(elements.lon_ascending_node_deg)

    return (
        pos_perifocal.rotate_z(arg_periapsis_rad)
        .rotate_x(inc_rad)
        .rotate_z(lon_ascending_node_rad)
    )


def orbital_period_days(
    semi_major_axis_au: float,
    central_mass_solar: float = 1.0,
) -> float:
    """Compute the Keplerian sidereal orbital period in days from Kepler's Third Law.

    Args:
        semi_major_axis_au: Semi-major axis ``a`` in Astronomical Units (> 0.0).
        central_mass_solar: Mass of the central body in solar masses (> 0.0, default 1.0).

    Returns:
        Sidereal orbital period ``T`` in Julian days.

    Raises:
        ValueError: If ``semi_major_axis_au <= 0.0`` or ``central_mass_solar <= 0.0``.
    """
    if semi_major_axis_au <= 0.0:
        raise ValueError("semi_major_axis_au must be > 0.0")
    if central_mass_solar <= 0.0:
        raise ValueError("central_mass_solar must be > 0.0")
    numerator = math.tau * math.sqrt((semi_major_axis_au**3) / central_mass_solar)
    return numerator / GAUSSIAN_GRAVITATIONAL_CONSTANT
