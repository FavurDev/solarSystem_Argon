"""Hierarchical logarithmic radial display scaling, body sizing, and focus-offset orbit sampling.

Provides the immutable ``DisplayScaleConfig`` configuration dataclass,
hierarchical logarithmic radial mappings ``heliocentric_distance_to_px`` and
``moon_distance_to_px``, piecewise body radius mapping ``body_display_radius_px``,
2D/3D astronomical-to-screen coordinate projection ``world_to_screen``, and
true focus-offset Keplerian orbital polyline sampling ``sample_orbit_screen_points``
with zero ``pygame`` dependencies (``TD-001``, ``TD-002``).
"""

# CHANGELOG:
# - Sprint 2: Created hierarchical logarithmic scaling, body sizing, and focus-offset orbit sampler.

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from solar_system.bodies import BodyCategory
from solar_system.kepler import OrbitalElements
from solar_system.vector import Vec3

DEFAULT_VIEWPORT_WIDTH: Final[int] = 1440
DEFAULT_VIEWPORT_HEIGHT: Final[int] = 1080
DEFAULT_SUN_CENTER: Final[tuple[int, int]] = (720, 540)
DEFAULT_R_MIN_AU: Final[float] = 0.30
DEFAULT_R_MAX_AU: Final[float] = 375.0
DEFAULT_PX_MIN: Final[float] = 52.0
DEFAULT_PX_MAX: Final[float] = 500.0
DEFAULT_MOON_R_MIN_AU: Final[float] = 0.00006
DEFAULT_MOON_R_MAX_AU: Final[float] = 0.04
DEFAULT_MOON_PX_MIN: Final[float] = 16.0
DEFAULT_MOON_PX_MAX: Final[float] = 28.0
DEFAULT_ORBIT_SAMPLES: Final[int] = 180

_LOGARITHMIC_RADIUS_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"planet", "dwarf", "moon", "comet"}
)
_STAR_RADIUS_PX: Final[int] = 18
_ASTEROID_RADIUS_THRESHOLD_KM: Final[float] = 25.0
_ASTEROID_SMALL_RADIUS_PX: Final[int] = 1
_ASTEROID_LARGE_RADIUS_PX: Final[int] = 2
_BODY_RADIUS_REF_KM: Final[float] = 500.0
_BODY_RADIUS_BASE_PX: Final[float] = 2.5
_BODY_RADIUS_LOG_SLOPE: Final[float] = 3.2
_BODY_RADIUS_MIN_PX: Final[int] = 2
_BODY_RADIUS_MAX_PX: Final[int] = 14


@dataclass(frozen=True, slots=True)
class DisplayScaleConfig:
    """Immutable configuration for hierarchical logarithmic distance scaling and viewport geometry.

    Attributes:
        viewport_width: Window width in pixels (default ``1440``).
        viewport_height: Window height in pixels (default ``1080``).
        sun_center: Pixel coordinates of the Sun / reference origin (default ``(720, 540)``).
        r_min_au: Lower AU clamp for heliocentric logarithmic scaling (default ``0.30``).
        r_max_au: Upper AU clamp for heliocentric logarithmic scaling (default ``375.0``).
        px_min: Minimum screen pixel radius for heliocentric orbits (default ``52.0``).
        px_max: Maximum screen pixel radius for heliocentric orbits (default ``500.0``).
        moon_r_min_au: Lower AU clamp for local planet-centered moon orbits (default ``0.00006``).
        moon_r_max_au: Upper AU clamp for local planet-centered moon orbits (default ``0.04``).
        moon_px_min: Minimum pixel offset from parent planet center (default ``16.0``).
        moon_px_max: Maximum pixel offset from parent planet center (default ``28.0``).
    """

    viewport_width: int = DEFAULT_VIEWPORT_WIDTH
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT
    sun_center: tuple[int, int] = DEFAULT_SUN_CENTER
    r_min_au: float = DEFAULT_R_MIN_AU
    r_max_au: float = DEFAULT_R_MAX_AU
    px_min: float = DEFAULT_PX_MIN
    px_max: float = DEFAULT_PX_MAX
    moon_r_min_au: float = DEFAULT_MOON_R_MIN_AU
    moon_r_max_au: float = DEFAULT_MOON_R_MAX_AU
    moon_px_min: float = DEFAULT_MOON_PX_MIN
    moon_px_max: float = DEFAULT_MOON_PX_MAX

    def __post_init__(self) -> None:
        """Validate positive finite bounds and strict min < max intervals.

        Raises:
            ValueError: If viewport dimensions are non-positive, ``sun_center`` is not
                a finite 2-tuple, numeric bounds are non-finite, or domain/range intervals
                violate ``0.0 < min < max`` (or ``0.0 <= px_min < px_max``).
        """
        if self.viewport_width <= 0 or self.viewport_height <= 0:
            raise ValueError("viewport_width and viewport_height must be positive integers")
        if (
            len(self.sun_center) != 2
            or not math.isfinite(self.sun_center[0])
            or not math.isfinite(self.sun_center[1])
        ):
            raise ValueError("sun_center must be a finite 2-tuple (x, y)")
        for val in (
            self.r_min_au,
            self.r_max_au,
            self.px_min,
            self.px_max,
            self.moon_r_min_au,
            self.moon_r_max_au,
            self.moon_px_min,
            self.moon_px_max,
        ):
            if not math.isfinite(val):
                raise ValueError("All DisplayScaleConfig numeric bounds must be finite")
        if self.r_min_au <= 0.0 or self.r_min_au >= self.r_max_au:
            raise ValueError("Require 0.0 < r_min_au < r_max_au")
        if self.px_min < 0.0 or self.px_min >= self.px_max:
            raise ValueError("Require 0.0 <= px_min < px_max")
        if self.moon_r_min_au <= 0.0 or self.moon_r_min_au >= self.moon_r_max_au:
            raise ValueError("Require 0.0 < moon_r_min_au < moon_r_max_au")
        if self.moon_px_min < 0.0 or self.moon_px_min >= self.moon_px_max:
            raise ValueError("Require 0.0 <= moon_px_min < moon_px_max")


DEFAULT_DISPLAY_SCALE_CONFIG: Final[DisplayScaleConfig] = DisplayScaleConfig()


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the closed interval ``[low, high]``.

    Args:
        value: Numeric scalar to clamp.
        low: Lower bound.
        high: Upper bound.

    Returns:
        Clamped float in ``[low, high]``.
    """
    if value < low:
        return low
    if value > high:
        return high
    return value


def heliocentric_distance_to_px(
    r_au: float,
    cfg: DisplayScaleConfig = DEFAULT_DISPLAY_SCALE_CONFIG,
) -> float:
    """Map heliocentric distance in AU to screen pixel radius in ``[cfg.px_min, cfg.px_max]``.

    Args:
        r_au: Heliocentric radial distance in Astronomical Units.
        cfg: Display scaling configuration (default ``DEFAULT_DISPLAY_SCALE_CONFIG``).

    Returns:
        Screen pixel radius in ``[cfg.px_min, cfg.px_max]``, or ``0.0`` if ``r_au <= 0.0``.

    Raises:
        ValueError: If ``r_au`` is boolean or non-finite (``NaN`` or ``inf``).
    """
    if isinstance(r_au, bool) or not math.isfinite(r_au):
        raise ValueError(f"r_au must be finite, got {r_au!r}")
    if r_au <= 0.0:
        return 0.0
    clamped_r_au = max(float(r_au), cfg.r_min_au)
    log_min = math.log10(cfg.r_min_au)
    log_max = math.log10(cfg.r_max_au)
    raw_u = (math.log10(clamped_r_au) - log_min) / (log_max - log_min)
    u = _clamp(raw_u, 0.0, 1.0)
    return float(cfg.px_min + u * (cfg.px_max - cfg.px_min))


def moon_distance_to_px(
    r_local_au: float,
    cfg: DisplayScaleConfig = DEFAULT_DISPLAY_SCALE_CONFIG,
) -> float:
    """Map planet-centered moon distance in AU to screen pixel offset.

    Args:
        r_local_au: Local planet-centered orbital distance in Astronomical Units.
        cfg: Display scaling configuration (default ``DEFAULT_DISPLAY_SCALE_CONFIG``).

    Returns:
        Screen pixel offset in ``[cfg.moon_px_min, cfg.moon_px_max]``, or ``0.0``
        if ``r_local_au <= 0.0``.

    Raises:
        ValueError: If ``r_local_au`` is boolean or non-finite (``NaN`` or ``inf``).
    """
    if isinstance(r_local_au, bool) or not math.isfinite(r_local_au):
        raise ValueError(f"r_local_au must be finite, got {r_local_au!r}")
    if r_local_au <= 0.0:
        return 0.0
    clamped_r_local = max(float(r_local_au), cfg.moon_r_min_au)
    log_min = math.log10(cfg.moon_r_min_au)
    log_max = math.log10(cfg.moon_r_max_au)
    raw_u = (math.log10(clamped_r_local) - log_min) / (log_max - log_min)
    u_moon = _clamp(raw_u, 0.0, 1.0)
    return float(cfg.moon_px_min + u_moon * (cfg.moon_px_max - cfg.moon_px_min))


def body_display_radius_px(
    radius_km: float,
    category: BodyCategory | str,
) -> int:
    """Map physical body mean radius (km) and category to integer screen pixel radius.

    Args:
        radius_km: Physical mean volumetric radius of the body in kilometers (> 0.0).
        category: ``BodyCategory`` literal (``"star"``, ``"planet"``, ``"moon"``,
            ``"dwarf"``, ``"asteroid"``, ``"comet"``) or case-insensitive string.

    Returns:
        Integer screen radius in pixels (``18`` for ``"star"``, ``1`` or ``2`` for
        ``"asteroid"``, or ``[2, 14]`` for ``"planet"``, ``"dwarf"``, ``"moon"``,
        and ``"comet"``).

    Raises:
        ValueError: If ``radius_km`` is boolean, non-finite, or ``<= 0.0``, or if
            ``category`` is not a supported body category.
    """
    if isinstance(radius_km, bool) or not math.isfinite(radius_km) or radius_km <= 0.0:
        raise ValueError(f"radius_km must be a finite positive number, got {radius_km!r}")
    normalized_category = str(getattr(category, "value", category)).strip().lower()
    if normalized_category == "star":
        return _STAR_RADIUS_PX
    if normalized_category == "asteroid":
        if radius_km < _ASTEROID_RADIUS_THRESHOLD_KM:
            return _ASTEROID_SMALL_RADIUS_PX
        return _ASTEROID_LARGE_RADIUS_PX
    if normalized_category in _LOGARITHMIC_RADIUS_CATEGORIES:
        effective_km = max(float(radius_km), _BODY_RADIUS_REF_KM)
        raw_px = round(
            _BODY_RADIUS_BASE_PX
            + _BODY_RADIUS_LOG_SLOPE * math.log10(effective_km / _BODY_RADIUS_REF_KM)
        )
        return max(_BODY_RADIUS_MIN_PX, min(_BODY_RADIUS_MAX_PX, int(raw_px)))
    raise ValueError(f"Unsupported body category: {category!r}")


def world_to_screen(
    pos_au: Vec3 | tuple[float, float],
    cfg: DisplayScaleConfig = DEFAULT_DISPLAY_SCALE_CONFIG,
    *,
    parent_screen_pos: tuple[int, int] | None = None,
    is_moon: bool = False,
    zoom: float = 1.0,
    pan_px: tuple[float, float] = (0.0, 0.0),
) -> tuple[int, int]:
    """Project 2D/3D AU coordinates to integer 2D screen pixel coordinates.

    Converts astronomical ecliptic coordinates (where ``+y`` points counter-clockwise /
    upward) into 2D screen pixel coordinates (where ``+y`` points downward) around
    ``cfg.sun_center`` or ``parent_screen_pos``, shifted by ``pan_px`` and scaled by
    ``zoom``.

    Args:
        pos_au: 3D ``Vec3`` or 2D ``(x_au, y_au)`` tuple in Astronomical Units.
        cfg: Display scaling configuration (default ``DEFAULT_DISPLAY_SCALE_CONFIG``).
        parent_screen_pos: Optional ``(x_px, y_px)`` screen origin for moons or orbits.
        is_moon: ``True`` to use ``moon_distance_to_px``; ``False`` for heliocentric.
        zoom: Positive scalar zoom multiplier (default ``1.0``).
        pan_px: ``(pan_x_px, pan_y_px)`` pixel offset added to the reference origin.

    Returns:
        Integer ``(screen_x, screen_y)`` pixel coordinates.

    Raises:
        TypeError: If ``pos_au`` is neither a ``Vec3`` nor a 2-tuple of numbers.
        ValueError: If ``zoom <= 0.0``, ``zoom`` is non-finite/bool, or coordinates /
            ``pan_px`` / ``parent_screen_pos`` contain invalid or non-finite values.
    """
    if isinstance(zoom, bool) or not math.isfinite(zoom) or zoom <= 0.0:
        raise ValueError(f"zoom must be a finite positive number, got {zoom!r}")
    if len(pan_px) != 2 or not math.isfinite(pan_px[0]) or not math.isfinite(pan_px[1]):
        raise ValueError(f"pan_px must be a finite 2-tuple, got {pan_px!r}")

    if isinstance(pos_au, Vec3):
        x_au, y_au, z_au = float(pos_au.x), float(pos_au.y), float(pos_au.z)
    elif isinstance(pos_au, tuple) and len(pos_au) == 2:
        x_au, y_au, z_au = float(pos_au[0]), float(pos_au[1]), 0.0
    else:
        raise TypeError(
            f"pos_au must be Vec3 or 2-tuple of floats, got {type(pos_au).__name__}"
        )
    if not (math.isfinite(x_au) and math.isfinite(y_au) and math.isfinite(z_au)):
        raise ValueError("pos_au coordinates must be finite numbers")

    if parent_screen_pos is not None:
        if (
            len(parent_screen_pos) != 2
            or not math.isfinite(parent_screen_pos[0])
            or not math.isfinite(parent_screen_pos[1])
        ):
            raise ValueError("parent_screen_pos must be a finite 2-tuple")
        base_x, base_y = float(parent_screen_pos[0]), float(parent_screen_pos[1])
    else:
        base_x, base_y = float(cfg.sun_center[0]), float(cfg.sun_center[1])

    origin_x = base_x + float(pan_px[0])
    origin_y = base_y + float(pan_px[1])

    r_au = math.hypot(x_au, y_au, z_au)
    if r_au <= 0.0:
        return (round(origin_x), round(origin_y))

    base_r_px = (
        moon_distance_to_px(r_au, cfg)
        if is_moon
        else heliocentric_distance_to_px(r_au, cfg)
    )
    scaled_r_px = base_r_px * float(zoom)

    ux = x_au / r_au
    uy = y_au / r_au
    screen_x = round(origin_x + scaled_r_px * ux)
    screen_y = round(origin_y - scaled_r_px * uy)
    return (int(screen_x), int(screen_y))


def sample_orbit_screen_points(
    elements: OrbitalElements,
    parent_screen_pos: tuple[int, int] = DEFAULT_SUN_CENTER,
    is_moon: bool = False,
    cfg: DisplayScaleConfig = DEFAULT_DISPLAY_SCALE_CONFIG,
    num_samples: int = DEFAULT_ORBIT_SAMPLES,
    *,
    zoom: float = 1.0,
) -> list[tuple[int, int]]:
    """Sample focus-offset Keplerian orbital points around true anomaly and project to screen.

    # IMPLEMENTATION DECISION: Sample num_samples true-anomaly angles nu_k = 2*pi*k/num_samples
    # using the exact polar conic equation r(nu_k) = a*(1 - e^2)/(1 + e*cos(nu_k)) relative to
    # the attracting focus (TD-002), rotated by the exact 3-1-3 Euler sequence of
    # keplerian_to_cartesian (including effective_inc_deg = 180.0 - inclination_deg when
    # orbital_period_days < 0.0 and inclination_deg > 90.0).
    # Rationale: Guarantees that the Sun or parent planet lies at the true Keplerian focus
    # rather than the geometric bounding-box center and that body markers lie directly on
    # their rendered orbital polylines for both prograde and retrograde orbits.
    # Alternatives: Screen-space ellipse bounding rect (rejected by TD-002).

    Args:
        elements: Validated ``OrbitalElements`` of the orbiting body.
        parent_screen_pos: Screen pixel coordinates of the attracting focus
            (default ``DEFAULT_SUN_CENTER = (720, 540)``).
        is_moon: ``True`` if sampling a local moon orbit around its parent planet.
        cfg: Display scaling configuration (default ``DEFAULT_DISPLAY_SCALE_CONFIG``).
        num_samples: Number of true-anomaly samples around ``[0, 2*pi)`` (default ``180``).
        zoom: Positive scalar zoom multiplier (default ``1.0``).

    Returns:
        List of ``num_samples`` ``(x_px, y_px)`` integer screen coordinates.

    Raises:
        ValueError: If ``num_samples < 3`` or ``zoom <= 0.0`` or non-finite/bool.
    """
    if isinstance(num_samples, bool) or int(num_samples) < 3:
        raise ValueError(f"num_samples must be an integer >= 3, got {num_samples!r}")
    if isinstance(zoom, bool) or not math.isfinite(zoom) or zoom <= 0.0:
        raise ValueError(f"zoom must be a finite positive number, got {zoom!r}")

    a_au = elements.semi_major_axis_au
    ecc = elements.eccentricity
    p_au = a_au * (1.0 - ecc * ecc)
    omega_rad = math.radians(elements.arg_periapsis_deg)
    lan_rad = math.radians(elements.lon_ascending_node_deg)
    if elements.orbital_period_days < 0.0 and elements.inclination_deg > 90.0:
        inc_deg = 180.0 - elements.inclination_deg
    else:
        inc_deg = elements.inclination_deg
    inc_rad = math.radians(inc_deg)

    points: list[tuple[int, int]] = []
    two_pi = 2.0 * math.pi
    for k in range(num_samples):
        nu_rad = (two_pi * float(k)) / float(num_samples)
        cos_nu = math.cos(nu_rad)
        sin_nu = math.sin(nu_rad)
        r_au = p_au / (1.0 + ecc * cos_nu)
        pos_orb = Vec3(r_au * cos_nu, r_au * sin_nu, 0.0)
        pos_ecl = pos_orb.rotate_z(omega_rad).rotate_x(inc_rad).rotate_z(lan_rad)
        screen_pt = world_to_screen(
            pos_ecl,
            cfg,
            parent_screen_pos=parent_screen_pos,
            is_moon=is_moon,
            zoom=zoom,
        )
        points.append(screen_pt)
    return points


__all__ = [
    "DEFAULT_DISPLAY_SCALE_CONFIG",
    "DEFAULT_MOON_PX_MAX",
    "DEFAULT_MOON_PX_MIN",
    "DEFAULT_MOON_R_MAX_AU",
    "DEFAULT_MOON_R_MIN_AU",
    "DEFAULT_ORBIT_SAMPLES",
    "DEFAULT_PX_MAX",
    "DEFAULT_PX_MIN",
    "DEFAULT_R_MAX_AU",
    "DEFAULT_R_MIN_AU",
    "DEFAULT_SUN_CENTER",
    "DEFAULT_VIEWPORT_HEIGHT",
    "DEFAULT_VIEWPORT_WIDTH",
    "DisplayScaleConfig",
    "body_display_radius_px",
    "heliocentric_distance_to_px",
    "moon_distance_to_px",
    "sample_orbit_screen_points",
    "world_to_screen",
]
