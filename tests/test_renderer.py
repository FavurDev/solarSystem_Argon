"""Offscreen Pygame 2D surface tests for SolarSystemRenderer (`solar_system.renderer`).

Uses `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` to exercise all 8
composited visual layers on a 1440x1080 offscreen `pygame.Surface` without
creating an OS display window. Imports `pygame` and `solar_system.renderer`
lazily inside fixtures/tests so `tests/conftest.py`'s headless collection audit
(`assert "pygame" not in sys.modules`) continues to pass.
"""

from __future__ import annotations

import importlib
import struct
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from solar_system.scaling import DEFAULT_DISPLAY_SCALE_CONFIG, world_to_screen
from solar_system.scenes import InputEvent, SceneFSM, SceneState
from solar_system.simulation import SimulationState


@pytest.fixture
def headless_renderer_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Any, Any, Any]]:
    """Initialize dummy SDL drivers, a 1440x1080 offscreen surface, and SolarSystemRenderer."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame = importlib.import_module("pygame")
    renderer_mod = importlib.import_module("solar_system.renderer")
    pygame.display.init()
    pygame.font.init()
    surface = pygame.Surface((1440, 1080))
    renderer = renderer_mod.SolarSystemRenderer(surface, DEFAULT_DISPLAY_SCALE_CONFIG)
    preloaded_keys = set(sys.modules)
    try:
        yield pygame, surface, renderer
    finally:
        pygame.font.quit()
        pygame.display.quit()
        for mod_name in list(sys.modules):
            if (
                mod_name == "pygame"
                or mod_name.startswith("pygame.")
                or mod_name == "solar_system.renderer"
                or mod_name not in preloaded_keys
            ):
                sys.modules.pop(mod_name, None)


def test_render_all_states_and_first_light_without_error(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify rendering TITLE, SIMULATION (+1/-1), PAUSED, first-light, and draw(fsm) succeeds."""
    # Arrange
    _, surface, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    fsm = SceneFSM(simulation=sim, initial_state=SceneState.TITLE)

    # Act
    renderer.render_frame(sim, SceneState.TITLE)
    renderer.render_frame(sim, SceneState.SIMULATION)
    sim.reverse_direction()
    renderer.render_frame(sim, SceneState.SIMULATION)
    sim.reverse_direction()
    renderer.render_frame(sim, SceneState.PAUSED)
    renderer.render_frame(sim, SceneState.SIMULATION, show_first_light_only=True)
    renderer.draw(fsm)

    # Assert
    assert surface.get_size() == (1440, 1080)
    assert renderer.surface is surface
    assert renderer.scale_config == DEFAULT_DISPLAY_SCALE_CONFIG


def test_sun_center_pixel_is_solar_yellow_and_backdrop_is_deep_space(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify the central Sun at (720, 540) is solar gold over a deep-space backdrop."""
    # Arrange
    _, surface, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    sim.show_hud = False
    sim.show_labels = False

    # Act
    renderer.render_frame(sim, SceneState.SIMULATION, show_first_light_only=True)
    sun_px = surface.get_at((720, 540))
    corona_px = surface.get_at((720 + 20, 540))
    backdrop_samples = [
        (surface.get_at((x, 2)).r, surface.get_at((x, 2)).g, surface.get_at((x, 2)).b)
        for x in range(2, 40)
    ]

    # Assert
    assert (sun_px.r, sun_px.g, sun_px.b) == (255, 204, 51)
    assert (corona_px.r, corona_px.g, corona_px.b) == (255, 228, 132)
    assert (6, 8, 20) in backdrop_samples


def test_distinct_pixel_buffers_across_scene_states_and_directions(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify TITLE, SIMULATION (+1/-1), PAUSED, and first-light produce 5 distinct RGB buffers."""
    # Arrange
    pygame, surface, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)

    # Act
    renderer.render_frame(sim, SceneState.TITLE)
    bytes_title = pygame.image.tobytes(surface, "RGB")
    sun_title = surface.get_at((720, 540))[:3]

    renderer.render_frame(sim, SceneState.SIMULATION)
    bytes_sim_fwd = pygame.image.tobytes(surface, "RGB")
    sun_fwd = surface.get_at((720, 540))[:3]

    sim.reverse_direction()
    renderer.render_frame(sim, SceneState.SIMULATION)
    bytes_sim_rev = pygame.image.tobytes(surface, "RGB")
    sun_rev = surface.get_at((720, 540))[:3]
    sim.reverse_direction()

    renderer.render_frame(sim, SceneState.PAUSED)
    bytes_paused = pygame.image.tobytes(surface, "RGB")
    sun_paused = surface.get_at((720, 540))[:3]

    renderer.render_frame(sim, SceneState.SIMULATION, show_first_light_only=True)
    bytes_first_light = pygame.image.tobytes(surface, "RGB")
    sun_first_light = surface.get_at((720, 540))[:3]

    # Assert
    buffers = [
        bytes_title,
        bytes_sim_fwd,
        bytes_sim_rev,
        bytes_paused,
        bytes_first_light,
    ]
    assert len(set(buffers)) == 5
    assert sun_title == (255, 204, 51)
    assert sun_fwd == (255, 204, 51)
    assert sun_rev == (255, 204, 51)
    assert sun_paused == (255, 204, 51)
    assert sun_first_light == (255, 204, 51)


def test_trail_surface_preallocated_identity_and_fading_trail_rendering(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify _trail_surface and _overlay_surface identities persist across 60 frames (TD-003)."""
    # Arrange
    pygame, surface, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    initial_trail_surface_id = id(renderer._trail_surface)
    initial_overlay_surface_id = id(renderer._overlay_surface)

    # Act
    for _ in range(60):
        sim.step(1.0 / 60.0)
        renderer.render_frame(sim, SceneState.SIMULATION)

    sim.show_trails = True
    renderer.render_frame(sim, SceneState.SIMULATION)
    bytes_with_trails = pygame.image.tobytes(surface, "RGB")

    sim.show_trails = False
    renderer.render_frame(sim, SceneState.SIMULATION)
    bytes_without_trails = pygame.image.tobytes(surface, "RGB")

    # Assert
    assert id(renderer._trail_surface) == initial_trail_surface_id
    assert id(renderer._overlay_surface) == initial_overlay_surface_id
    assert bytes_with_trails != bytes_without_trails


def test_layer_toggles_orbits_kirkwood_labels_hud_and_camera(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify layer toggles (orbits, Kirkwood, labels, HUD) and camera pan shift pixel output."""
    # Arrange
    pygame, surface, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    sim.show_kirkwood = True

    # Act
    renderer.render_frame(sim, SceneState.SIMULATION)
    base_bytes = pygame.image.tobytes(surface, "RGB")

    sim.show_orbits = False
    renderer.render_frame(sim, SceneState.SIMULATION)
    no_orbits_bytes = pygame.image.tobytes(surface, "RGB")
    sim.show_orbits = True

    sim.show_kirkwood = False
    renderer.render_frame(sim, SceneState.SIMULATION)
    no_kirkwood_bytes = pygame.image.tobytes(surface, "RGB")
    sim.show_kirkwood = True

    sim.show_labels = False
    renderer.render_frame(sim, SceneState.SIMULATION)
    no_labels_bytes = pygame.image.tobytes(surface, "RGB")
    sim.show_labels = True

    sim.show_hud = False
    renderer.render_frame(sim, SceneState.SIMULATION)
    no_hud_bytes = pygame.image.tobytes(surface, "RGB")
    sim.show_hud = True

    sim.pan_by_pixels(50.0, -30.0)
    renderer.render_frame(sim, SceneState.SIMULATION, show_first_light_only=True)
    panned_sun_px = surface.get_at((720 + 50, 540 - 30))[:3]

    # Assert
    assert base_bytes != no_orbits_bytes
    assert base_bytes != no_kirkwood_bytes
    assert base_bytes != no_labels_bytes
    assert base_bytes != no_hud_bytes
    assert panned_sun_px == (255, 204, 51)


def test_scene_fsm_polymorphic_draw_routing(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify renderer.draw(fsm) and render_frame(fsm) route across TITLE -> SIMULATION -> PAUSED."""
    # Arrange
    pygame, surface, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    fsm = SceneFSM(simulation=sim, initial_state=SceneState.TITLE)

    # Act
    renderer.draw(fsm)
    title_bytes = pygame.image.tobytes(surface, "RGB")

    fsm.handle_event(InputEvent.KEY_RETURN)
    renderer.draw(fsm)
    sim_bytes = pygame.image.tobytes(surface, "RGB")

    fsm.handle_event(InputEvent.KEY_P)
    renderer.render_frame(fsm)
    paused_bytes = pygame.image.tobytes(surface, "RGB")

    # Assert
    assert fsm.state == SceneState.PAUSED
    assert len({title_bytes, sim_bytes, paused_bytes}) == 3


def test_save_screenshot_writes_valid_png(
    headless_renderer_env: tuple[Any, Any, Any],
    tmp_path: Path,
) -> None:
    """Verify save_screenshot writes a valid 1440x1080 PNG with non-uniform pixels."""
    # Arrange
    pygame, _, renderer = headless_renderer_env
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    out_file = tmp_path / "nested" / "frame.png"

    # Act
    renderer.render_frame(sim, SceneState.SIMULATION)
    saved_path = renderer.save_screenshot(out_file)
    data = saved_path.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    loaded_surface = pygame.image.load(str(saved_path))
    loaded_rgb = pygame.image.tobytes(loaded_surface, "RGB")
    first_triplet = loaded_rgb[:3]

    # Assert
    assert saved_path == out_file
    assert saved_path.exists()
    assert len(data) > 1000
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    assert (width, height) == (1440, 1080)
    assert any(
        loaded_rgb[idx : idx + 3] != first_triplet
        for idx in range(0, len(loaded_rgb), 300)
    )


def test_moon_and_ring_rendering_visibility(
    headless_renderer_env: tuple[Any, Any, Any],
) -> None:
    """Verify Saturn, Earth's Moon, and SolarSystemRenderer(None) ValueError behavior."""
    # Arrange
    _, surface, renderer = headless_renderer_env
    renderer_mod = importlib.import_module("solar_system.renderer")
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    sim.show_hud = False
    sim.show_labels = False

    # Act
    renderer.render_frame(sim, SceneState.SIMULATION, show_first_light_only=True)
    saturn_pos = sim.cached_positions_au["Saturn"]
    saturn_px = world_to_screen(saturn_pos, DEFAULT_DISPLAY_SCALE_CONFIG)
    saturn_color = sim.bodies_by_name["Saturn"].style.color_rgb

    earth_pos = sim.cached_positions_au["Earth"]
    moon_pos = sim.cached_positions_au["Moon"]
    earth_px = world_to_screen(earth_pos, DEFAULT_DISPLAY_SCALE_CONFIG)
    moon_rel_au = moon_pos - earth_pos
    moon_px = world_to_screen(
        moon_rel_au,
        DEFAULT_DISPLAY_SCALE_CONFIG,
        parent_screen_pos=earth_px,
        is_moon=True,
    )
    moon_color = sim.bodies_by_name["Moon"].style.color_rgb

    # Assert
    assert surface.get_at(saturn_px)[:3] == saturn_color
    assert surface.get_at(moon_px)[:3] == moon_color
    with pytest.raises(ValueError, match="surface"):
        renderer_mod.SolarSystemRenderer(None)