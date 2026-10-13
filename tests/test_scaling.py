"""Headless unit tests for hybrid logarithmic radial display scaling (solar_system.scaling).

Covers Sub-suite 6 from the Phase 1 Sprint 2 Task 1 specification:
- DisplayScaleConfig defaults, immutability, and __post_init__ validation
- heliocentric_distance_to_px zero origin, clamping, and logarithmic interpolation
- Strict radial monotonicity across heliocentric named bodies and outer TNOs
- moon_distance_to_px bounds and Galilean moon ordering
- body_display_radius_px piecewise sizing and input validation
- world_to_screen origin mapping, +y AU to -y screen inversion, pan, and zoom
- sample_orbit_screen_points 180-vertex viewport bounds and focus-offset (TD-002)
- AST zero-pygame import check (TD-001)
"""

from __future__ import annotations

import ast
import dataclasses
import math
from pathlib import Path

import pytest

from solar_system.bodies import (
    BodyCategory,
    build_named_bodies,
    generate_asteroid_belt,
)
from solar_system.kepler import (
    J2000_JD,
    OrbitalElements,
    keplerian_to_cartesian,
)
from solar_system.scaling import (
    DEFAULT_DISPLAY_SCALE_CONFIG,
    DisplayScaleConfig,
    body_display_radius_px,
    heliocentric_distance_to_px,
    moon_distance_to_px,
    sample_orbit_screen_points,
    world_to_screen,
)
from solar_system.vector import Vec3


def test_display_scale_config_defaults_and_validation() -> None:
    """Verify DisplayScaleConfig default attributes, frozen immutability, and validation."""
    # Arrange & Act
    config = DisplayScaleConfig()

    # Assert
    assert config == DEFAULT_DISPLAY_SCALE_CONFIG
    assert config.viewport_width == 1440
    assert config.viewport_height == 1080
    assert config.sun_center == (720, 540)
    assert config.r_min_au == pytest.approx(0.30)
    assert config.r_max_au == pytest.approx(375.0)
    assert config.px_min == pytest.approx(52.0)
    assert config.px_max == pytest.approx(500.0)
    assert config.moon_r_min_au == pytest.approx(0.00006)
    assert config.moon_r_max_au == pytest.approx(0.04)
    assert config.moon_px_min == pytest.approx(16.0)
    assert config.moon_px_max == pytest.approx(28.0)

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.px_max = 600.0  # type: ignore[misc]

    with pytest.raises(ValueError, match="viewport"):
        DisplayScaleConfig(viewport_width=0)
    with pytest.raises(ValueError, match="r_min_au"):
        DisplayScaleConfig(r_min_au=10.0, r_max_au=5.0)
    with pytest.raises(ValueError, match="px_min"):
        DisplayScaleConfig(px_min=500.0, px_max=100.0)
    with pytest.raises(ValueError, match="moon_r_min_au"):
        DisplayScaleConfig(moon_r_min_au=0.05, moon_r_max_au=0.04)
    with pytest.raises(ValueError, match="moon_px_min"):
        DisplayScaleConfig(moon_px_min=30.0, moon_px_max=20.0)


def test_heliocentric_distance_to_px_zero_and_clamping() -> None:
    """Verify zero mapping, lower/upper clamping, 1 AU interpolation, and error handling."""
    # Arrange
    config = DisplayScaleConfig()
    expected_1au = 52.0 + (500.0 - 52.0) * (
        math.log10(1.0 / 0.30) / math.log10(375.0 / 0.30)
    )

    # Act
    px_zero = heliocentric_distance_to_px(0.0, config)
    px_neg = heliocentric_distance_to_px(-1.5, config)
    px_sub_min = heliocentric_distance_to_px(0.10, config)
    px_at_min = heliocentric_distance_to_px(0.30, config)
    px_1au = heliocentric_distance_to_px(1.0, config)
    px_at_max = heliocentric_distance_to_px(375.0, config)
    px_super_max = heliocentric_distance_to_px(506.0, config)

    # Assert
    assert px_zero == 0.0
    assert px_neg == 0.0
    assert px_sub_min == pytest.approx(52.0)
    assert px_at_min == pytest.approx(52.0)
    assert px_1au == pytest.approx(expected_1au, rel=1e-12)
    assert px_at_max == pytest.approx(500.0)
    assert px_super_max == pytest.approx(500.0)

    with pytest.raises(ValueError, match="r_au"):
        heliocentric_distance_to_px(float("nan"), config)
    with pytest.raises(ValueError, match="r_au"):
        heliocentric_distance_to_px(float("inf"), config)
    with pytest.raises(ValueError, match="r_au"):
        heliocentric_distance_to_px(True, config)


def test_heliocentric_radial_monotonicity_across_catalog_and_tnos() -> None:
    """Verify strict radial ordering from Mercury through Eris and Sedna perihelion."""
    # Arrange
    bodies = {b.name: b for b in build_named_bodies()}
    ordered_names = [
        "Mercury",
        "Venus",
        "Earth",
        "Mars",
        "Ceres",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
        "Haumea",
        "Makemake",
        "Eris",
    ]
    fallback_au = {
        "Mercury": 0.387098,
        "Venus": 0.723332,
        "Earth": 1.000000,
        "Mars": 1.523679,
        "Ceres": 2.7675,
        "Jupiter": 5.2044,
        "Saturn": 9.5826,
        "Uranus": 19.2184,
        "Neptune": 30.1104,
        "Pluto": 39.482,
        "Haumea": 43.13,
        "Makemake": 45.79,
        "Eris": 67.78,
    }
    distances_au: list[float] = []
    for name in ordered_names:
        if name in bodies:
            body_obj = bodies[name]
            orbit = getattr(body_obj, "orbit", None) or getattr(body_obj, "elements", None)
            assert orbit is not None
            distances_au.append(orbit.semi_major_axis_au)
        else:
            distances_au.append(fallback_au[name])

    sedna_perihelion_au = 506.0 * (1.0 - 0.8496)
    sedna_semi_major_au = 506.0
    all_distances_au = [*distances_au, sedna_perihelion_au, sedna_semi_major_au]

    # Act
    radii_px = [heliocentric_distance_to_px(r) for r in all_distances_au]

    # Assert
    for idx in range(len(radii_px) - 1):
        assert radii_px[idx] < radii_px[idx + 1], (
            f"Expected strict monotonicity at index {idx}: "
            f"{radii_px[idx]} >= {radii_px[idx + 1]}"
        )
    assert all(52.0 <= px <= 500.0 for px in radii_px)
    assert radii_px[-1] == pytest.approx(500.0)


def test_moon_distance_to_px_bounds_and_galilean_monotonicity() -> None:
    """Verify catalog moons map into [16, 28] px and Galilean moons order strictly."""
    # Arrange
    bodies = {b.name: b for b in build_named_bodies()}
    moon_bodies = [
        b
        for b in bodies.values()
        if getattr(b, "parent_name", None) not in (None, "Sun")
    ]
    galilean_names = ["Io", "Europa", "Ganymede", "Callisto"]

    # Act
    moon_px_map: dict[str, float] = {}
    for moon in moon_bodies:
        orbit = getattr(moon, "orbit", None) or getattr(moon, "elements", None)
        assert orbit is not None
        moon_px_map[moon.name] = moon_distance_to_px(orbit.semi_major_axis_au)

    galilean_px = [moon_px_map[name] for name in galilean_names]
    zero_px = moon_distance_to_px(0.0)

    # Assert
    assert zero_px == 0.0
    assert len(moon_bodies) >= 9
    for name, px in moon_px_map.items():
        assert 16.0 <= px <= 28.0, f"Moon {name} mapped outside [16, 28] px: {px}"
    assert galilean_px[0] < galilean_px[1] < galilean_px[2] < galilean_px[3]

    with pytest.raises(ValueError, match="r_local_au"):
        moon_distance_to_px(float("nan"))
    with pytest.raises(ValueError, match="r_local_au"):
        moon_distance_to_px(False)


def test_body_display_radius_px_categories_and_monotonicity() -> None:
    """Verify star=18, asteroid=1..2, and planet/dwarf/moon/comet radii in [2, 14] px."""
    # Arrange
    bodies = {b.name: b for b in build_named_bodies()}
    asteroids = generate_asteroid_belt(count=20, seed=42)
    star_cat: BodyCategory = "star"
    planet_cat: BodyCategory = "planet"
    dwarf_cat: BodyCategory = "dwarf"
    comet_cat: BodyCategory = "comet"
    asteroid_cat: BodyCategory = "asteroid"

    # Act
    sun_r = body_display_radius_px(695_700.0, star_cat)
    small_ast_r = body_display_radius_px(5.0, asteroid_cat)
    large_ast_r = body_display_radius_px(50.0, "asteroid")
    mercury_r = body_display_radius_px(bodies["Mercury"].radius_km, planet_cat)
    earth_r = body_display_radius_px(bodies["Earth"].radius_km, planet_cat)
    jupiter_r = body_display_radius_px(bodies["Jupiter"].radius_km, planet_cat)
    ceres_r = body_display_radius_px(bodies["Ceres"].radius_km, dwarf_cat)
    halley_r = body_display_radius_px(bodies["1P/Halley"].radius_km, comet_cat)
    belt_radii = [
        body_display_radius_px(a.radius_km, a.category) for a in asteroids
    ]

    # Assert
    assert sun_r == 18
    assert small_ast_r == 1
    assert large_ast_r == 2
    assert all(r in (1, 2) for r in belt_radii)
    for r in (mercury_r, earth_r, jupiter_r, ceres_r, halley_r):
        assert 2 <= r <= 14
    assert earth_r >= mercury_r
    assert jupiter_r > earth_r


def test_body_display_radius_px_invalid_inputs() -> None:
    """Verify ValueError on non-positive, non-finite, bool, or unknown category."""
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="radius_km"):
        body_display_radius_px(0.0, "planet")
    with pytest.raises(ValueError, match="radius_km"):
        body_display_radius_px(-100.0, "planet")
    with pytest.raises(ValueError, match="radius_km"):
        body_display_radius_px(float("nan"), "planet")
    with pytest.raises(ValueError, match="radius_km"):
        body_display_radius_px(True, "planet")
    with pytest.raises(ValueError, match="category"):
        body_display_radius_px(6371.0, "quasar")


def test_world_to_screen_origin_y_inversion_pan_and_zoom() -> None:
    """Verify origin -> (720, 540), +y AU -> y_screen < 540, pan_px, and zoom."""
    # Arrange
    config = DisplayScaleConfig()

    # Act
    origin_screen = world_to_screen(Vec3(0.0, 0.0, 0.0), cfg=config)
    origin_tuple = world_to_screen((0.0, 0.0), cfg=config)
    pos_x_screen = world_to_screen(Vec3(1.0, 0.0, 0.0), cfg=config)
    pos_y_screen = world_to_screen(Vec3(0.0, 1.0, 0.0), cfg=config)
    zoomed_screen = world_to_screen(Vec3(1.0, 0.0, 0.0), cfg=config, zoom=2.0)
    panned_screen = world_to_screen(
        Vec3(0.0, 0.0, 0.0), cfg=config, pan_px=(30.0, -20.0)
    )
    moon_screen = world_to_screen(
        Vec3(0.00257, 0.0, 0.0),
        cfg=config,
        parent_screen_pos=(900, 540),
        is_moon=True,
    )

    # Assert
    assert origin_screen == (720, 540)
    assert origin_tuple == (720, 540)
    assert pos_x_screen[0] > 720 and pos_x_screen[1] == 540
    assert pos_y_screen[0] == 720 and pos_y_screen[1] < 540
    assert (zoomed_screen[0] - 720) == pytest.approx(
        2 * (pos_x_screen[0] - 720), abs=1
    )
    assert panned_screen == (750, 520)
    assert 900 + 16 <= moon_screen[0] <= 900 + 28
    assert moon_screen[1] == 540

    with pytest.raises(ValueError, match="zoom"):
        world_to_screen(Vec3(1.0, 0.0, 0.0), zoom=0.0)
    with pytest.raises(ValueError, match="pan_px"):
        world_to_screen(Vec3(1.0, 0.0, 0.0), pan_px=(10.0,))  # type: ignore[arg-type]


def test_sample_orbit_screen_points_180_vertices_within_viewport() -> None:
    """Verify 180 vertices for all heliocentric catalog bodies stay within 1440x1080."""
    # Arrange
    config = DisplayScaleConfig()
    bodies = [
        b
        for b in build_named_bodies()
        if getattr(b, "parent_name", None) in (None, "Sun")
        and (getattr(b, "orbit", None) or getattr(b, "elements", None)) is not None
    ]

    # Act & Assert
    assert len(bodies) >= 15
    for body in bodies:
        orbit = body.elements
        assert orbit is not None
        points = sample_orbit_screen_points(orbit, cfg=config, num_samples=180)
        assert len(points) == 180
        for x_px, y_px in points:
            assert isinstance(x_px, int) and isinstance(y_px, int)
            assert 0 <= x_px < config.viewport_width, (
                f"{body.name} x={x_px} outside viewport"
            )
            assert 0 <= y_px < config.viewport_height, (
                f"{body.name} y={y_px} outside viewport"
            )


def test_sample_orbit_focus_offset_perihelion_closer_than_aphelion() -> None:
    """Verify TD-002: perihelion (nu=0) is strictly closer to Sun focus than aphelion (nu=pi)."""
    # Arrange
    config = DisplayScaleConfig()
    sun_x, sun_y = config.sun_center
    eccentric_orbits = [
        OrbitalElements(
            semi_major_axis_au=0.387098,
            eccentricity=0.205630,
            inclination_deg=7.005,
            lon_ascending_node_deg=48.331,
            arg_periapsis_deg=29.124,
            mean_anomaly_epoch_deg=174.796,
            orbital_period_days=87.969,
        ),
        OrbitalElements(
            semi_major_axis_au=506.0,
            eccentricity=0.8496,
            inclination_deg=11.93,
            lon_ascending_node_deg=144.26,
            arg_periapsis_deg=311.29,
            mean_anomaly_epoch_deg=358.12,
            orbital_period_days=4_150_000.0,
        ),
        OrbitalElements(
            semi_major_axis_au=17.834,
            eccentricity=0.96714,
            inclination_deg=162.26,
            lon_ascending_node_deg=58.42,
            arg_periapsis_deg=111.33,
            mean_anomaly_epoch_deg=38.38,
            orbital_period_days=27_509.0,
        ),
    ]

    # Act & Assert
    for orbit in eccentric_orbits:
        pts = sample_orbit_screen_points(orbit, cfg=config, num_samples=180)
        peri_pt = pts[0]  # nu = 0 (perihelion)
        aph_pt = pts[90]  # nu = pi (aphelion)
        dist_peri = math.hypot(peri_pt[0] - sun_x, peri_pt[1] - sun_y)
        dist_aph = math.hypot(aph_pt[0] - sun_x, aph_pt[1] - sun_y)
        assert dist_peri < dist_aph, (
            f"Focus offset violated for e={orbit.eccentricity}: "
            f"d_peri={dist_peri}, d_aph={dist_aph}"
        )


def test_sample_orbit_matches_keplerian_to_cartesian_at_perihelion() -> None:
    """Verify sample_orbit_screen_points at nu=0 matches keplerian_to_cartesian at M0=0."""
    # Arrange
    config = DisplayScaleConfig()
    orbit_at_perihelion = OrbitalElements(
        semi_major_axis_au=17.834,
        eccentricity=0.96714,
        inclination_deg=162.26,
        lon_ascending_node_deg=58.42,
        arg_periapsis_deg=111.33,
        mean_anomaly_epoch_deg=0.0,
        orbital_period_days=27_509.0,
    )

    # Act
    pts = sample_orbit_screen_points(orbit_at_perihelion, cfg=config, num_samples=180)
    pos_3d = keplerian_to_cartesian(orbit_at_perihelion, J2000_JD)
    expected_screen = world_to_screen(pos_3d, cfg=config)

    # Assert
    assert pts[0] == expected_screen


def test_scaling_module_has_zero_pygame_imports() -> None:
    """Verify TD-001: src/solar_system/scaling.py contains zero pygame imports via AST."""
    # Arrange
    scaling_path = (
        Path(__file__).resolve().parents[1] / "src" / "solar_system" / "scaling.py"
    )

    # Act
    source = scaling_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(scaling_path))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    # Assert
    assert "pygame" not in imported_modules