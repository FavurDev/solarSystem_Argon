"""Headless unit tests for SimulationState speed, frame, preset, and camera controls."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from solar_system.bodies import J2000_EPOCH_JD, build_named_bodies
from solar_system.simulation import (
    DEFAULT_SPEED_INDEX,
    MAX_ZOOM_MULTIPLIER,
    MIN_ZOOM_MULTIPLIER,
    SPEED_LADDER_DAYS_PER_SEC,
    Simulation,
    SimulationState,
)


def test_create_default_initializes_fields_and_non_asteroid_trails() -> None:
    """Verify create_default sets all 20 fields and initializes 25 non-asteroid trails."""
    # Arrange & Act
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    expected_named_count = len(build_named_bodies())

    # Assert
    assert Simulation is SimulationState
    assert sim.julian_date == J2000_EPOCH_JD
    assert sim.initial_jd == J2000_EPOCH_JD
    assert sim.speed_index == DEFAULT_SPEED_INDEX == 3
    assert sim.current_speed_days_per_sec == 1.0
    assert sim.direction == 1
    assert sim.paused is False
    assert sim.active_frame_name == "Sun"
    assert sim.active_scene_id == 1
    assert sim.zoom_multiplier == 1.0
    assert sim.pan_offset_px == (0.0, 0.0)
    assert sim.selected_body_name is None
    assert sim.show_labels is True
    assert sim.show_trails is True
    assert sim.show_orbits is True
    assert sim.show_kirkwood is False
    assert sim.show_hud is True
    assert expected_named_count == 25
    assert len(sim.bodies) == 385
    assert len(sim.bodies_by_name) == 385
    assert len(sim.trails) == 25
    for body_name, trail in sim.trails.items():
        assert sim.bodies_by_name[body_name].category != "asteroid"
        assert trail.frame_name == "Sun"
        assert len(trail) == 0
    assert "Sun" in sim.frames_by_name
    assert "Mars" in sim.frames_by_name
    assert "Mercury" in sim.frames_by_name
    assert "Venus" in sim.frames_by_name
    assert sim.cached_positions_au["Sun"].norm() < 1e-12

    with pytest.raises(ValueError):
        SimulationState.create_default(initial_jd=float("nan"))


def test_speed_up_and_slow_down_clamp_within_ladder_bounds() -> None:
    """Verify speed_up and slow_down traverse SPEED_LADDER_DAYS_PER_SEC and clamp cleanly."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)

    # Act & Assert
    current_speed = sim.current_speed_days_per_sec
    for _ in range(25):
        current_speed = sim.speed_up()

    assert sim.speed_index == len(SPEED_LADDER_DAYS_PER_SEC) - 1 == 10
    assert current_speed == 1826.25
    assert sim.current_speed_days_per_sec == 1826.25

    for _ in range(25):
        current_speed = sim.slow_down()

    assert sim.speed_index == 0
    assert current_speed == 0.01
    assert sim.current_speed_days_per_sec == 0.01


def test_effective_rate_days_per_sec_reflects_pause_and_direction() -> None:
    """Verify effective_rate_days_per_sec reflects speed, direction, and paused state."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)

    # Act & Assert
    assert sim.effective_rate_days_per_sec == 1.0
    sim.reverse_direction()
    assert sim.effective_rate_days_per_sec == -1.0
    sim.toggle_pause()
    assert sim.effective_rate_days_per_sec == 0.0


def test_set_reference_frame_mars_clears_trails_and_centers_origin() -> None:
    """Verify set_reference_frame clears trails, updates trail frame_name, and centers origin."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)
    for _ in range(5):
        sim.step(dt_wall_sec=1.0)
    assert len(sim.trails["Earth"]) == 5
    assert sim.active_frame_name == "Sun"

    # Act
    sim.set_reference_frame(frame_name="Mars")

    # Assert
    assert sim.active_frame_name == "Mars"
    for trail in sim.trails.values():
        assert len(trail) == 0
        assert trail.frame_name == "Mars"
    assert sim.cached_positions_au["Mars"].norm() < 1e-12

    sim.step(dt_wall_sec=1.0)
    assert len(sim.trails["Earth"]) == 1
    assert sim.trails["Earth"].frame_name == "Mars"

    for extra_frame in ("Uranus", "Neptune", "Mercury", "Venus"):
        sim.set_reference_frame(frame_name=extra_frame)
        assert sim.active_frame_name == extra_frame
        assert sim.cached_positions_au[extra_frame].norm() < 1e-12


def test_set_reference_frame_unknown_raises_key_error() -> None:
    """Verify set_reference_frame raises KeyError on unknown frame without mutating state."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)

    # Act & Assert
    with pytest.raises(KeyError):
        sim.set_reference_frame("UnknownFrameXYZ")
    assert sim.active_frame_name == "Sun"


def test_apply_scene_presets_1_through_5_and_overrides() -> None:
    """Verify apply_scene_preset configures presets 1..5, supports overrides, and validates inputs."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)
    sim.pan_by_pixels(dx_px=120.0, dy_px=-45.0)

    # Act & Assert
    sim.apply_scene_preset(scene_id=1)
    assert sim.active_scene_id == 1
    assert sim.active_frame_name == "Sun"
    assert sim.zoom_multiplier == 1.0
    assert sim.show_kirkwood is False
    assert sim.selected_body_name == "Earth"
    assert sim.pan_offset_px == (0.0, 0.0)

    sim.apply_scene_preset(scene_id=2)
    assert sim.active_scene_id == 2
    assert sim.active_frame_name == "Sun"
    assert sim.zoom_multiplier == 0.15
    assert sim.show_kirkwood is False
    assert sim.selected_body_name == "Saturn"

    sim.apply_scene_preset(scene_id=3)
    assert sim.active_scene_id == 3
    assert sim.active_frame_name == "Earth"
    assert sim.selected_body_name == "Moon"
    assert sim.zoom_multiplier == 18.0
    assert sim.show_kirkwood is False
    assert sim.pan_offset_px == (0.0, 0.0)

    sim.apply_scene_preset(scene_id=4)
    assert sim.active_scene_id == 4
    assert sim.active_frame_name == "Mars"
    assert sim.zoom_multiplier == 2.5
    assert sim.show_kirkwood is False
    assert sim.selected_body_name == "Mars"

    sim.apply_scene_preset(scene_id=5)
    assert sim.active_scene_id == 5
    assert sim.active_frame_name == "Sun"
    assert sim.zoom_multiplier == 0.55
    assert sim.show_kirkwood is True
    assert sim.selected_body_name == "Jupiter"

    sim.apply_scene_preset(
        scene_id=2,
        frame_name="Mars",
        zoom_multiplier=999.0,
        show_kirkwood=True,
        selected_body_name="Mars",
    )
    assert sim.active_scene_id == 2
    assert sim.active_frame_name == "Mars"
    assert sim.zoom_multiplier == MAX_ZOOM_MULTIPLIER == 50.0
    assert sim.show_kirkwood is True
    assert sim.selected_body_name == "Mars"

    with pytest.raises(ValueError):
        sim.apply_scene_preset(0)

    with pytest.raises(ValueError):
        sim.apply_scene_preset(6)

    with pytest.raises(ValueError):
        sim.apply_scene_preset(True)

    with pytest.raises(ValueError):
        sim.apply_scene_preset(1, zoom_multiplier=-1.0)

    with pytest.raises(ValueError):
        sim.apply_scene_preset(1, zoom_multiplier=float("nan"))

    with pytest.raises(KeyError):
        sim.apply_scene_preset(1, selected_body_name="UnknownBody")


def test_select_body_adjust_zoom_and_pan_by_pixels() -> None:
    """Verify select_body, adjust_zoom clamping, and pan_by_pixels accumulation and validation."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)

    # Act & Assert
    sim.select_body(body_name="Saturn")
    assert sim.selected_body_name == "Saturn"
    sim.select_body(body_name=None)
    assert sim.selected_body_name is None

    with pytest.raises(KeyError):
        sim.select_body("NotABody")

    z1 = sim.adjust_zoom(factor=2.5)
    assert z1 == 2.5
    assert sim.zoom_multiplier == 2.5

    z_max = sim.adjust_zoom(factor=100.0)
    assert z_max == MAX_ZOOM_MULTIPLIER == 50.0

    z_min = sim.adjust_zoom(factor=0.0001)
    assert z_min == MIN_ZOOM_MULTIPLIER == 0.1

    with pytest.raises(ValueError):
        sim.adjust_zoom(0.0)

    with pytest.raises(ValueError):
        sim.adjust_zoom(-2.0)

    with pytest.raises(ValueError):
        sim.adjust_zoom(float("nan"))

    p1 = sim.pan_by_pixels(dx_px=15.5, dy_px=-20.25)
    assert p1 == (15.5, -20.25)
    p2 = sim.pan_by_pixels(dx_px=-5.5, dy_px=10.25)
    assert p2 == (10.0, -10.0)
    assert sim.pan_offset_px == (10.0, -10.0)

    with pytest.raises(ValueError):
        sim.pan_by_pixels(float("nan"), 0.0)

    with pytest.raises(ValueError):
        sim.pan_by_pixels(0.0, float("inf"))


def test_simulation_module_has_zero_pygame_imports() -> None:
    """Verify src/solar_system/simulation.py has zero pygame imports statically and at runtime."""
    # Arrange
    sim_path = Path(__file__).resolve().parents[1] / "src" / "solar_system" / "simulation.py"
    source = sim_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(sim_path))

    # Act
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
    positions = SimulationState.create_default(asteroid_count=8).step(0.5)

    # Assert
    for mod_name in imported_modules:
        assert not mod_name.startswith("pygame"), f"Forbidden pygame import found: {mod_name}"
    assert "pygame" not in sys.modules
    assert len(positions) == 33
