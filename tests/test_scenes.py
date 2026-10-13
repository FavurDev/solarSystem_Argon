"""Headless unit tests for the solar_system.scenes finite-state machine and package exports."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import solar_system
from solar_system.scenes import (
    ZOOM_IN_FACTOR,
    ZOOM_OUT_FACTOR,
    InputEvent,
    PausedScene,
    SceneFSM,
    SceneState,
    SimulationScene,
    TitleScene,
)
from solar_system.simulation import SPEED_LADDER_DAYS_PER_SEC, SimulationState


def test_scene_fsm_state_transitions_and_pause_sync() -> None:
    """Verify TITLE -> SIMULATION -> PAUSED -> SIMULATION -> QUIT transitions and pause sync."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)
    fsm = SceneFSM(simulation=sim)

    # Act & Assert (Step 1 — Initial TITLE state)
    assert fsm.state == SceneState.TITLE
    assert fsm.current_state == SceneState.TITLE
    assert fsm.is_running is True
    assert fsm.active_scene == fsm.title_scene
    assert isinstance(fsm.title_scene, TitleScene)
    assert isinstance(fsm.simulation_scene, SimulationScene)
    assert isinstance(fsm.paused_scene, PausedScene)

    for noop_event in (
        InputEvent.KEY_SPACE,
        InputEvent.KEY_P,
        InputEvent.KEY_PLUS,
        InputEvent.KEY_MINUS,
        InputEvent.KEY_R,
        InputEvent.KEY_TAB,
        InputEvent.KEY_DIGIT_1,
        InputEvent.KEY_OTHER,
    ):
        assert fsm.handle_event(noop_event) == SceneState.TITLE
        assert fsm.state == SceneState.TITLE

    # Act & Assert (Step 2 — TITLE -> SIMULATION on KEY_RETURN, including when pre-paused)
    sim.paused = True
    s1 = fsm.handle_event(InputEvent.KEY_RETURN)
    assert s1 == SceneState.SIMULATION
    assert fsm.state.value == "SIMULATION"
    assert fsm.current_state.value == "SIMULATION"
    assert sim.paused is False
    assert isinstance(fsm.active_scene, SimulationScene)

    # Act & Assert (Step 3 — SIMULATION -> PAUSED on KEY_P)
    s2 = fsm.handle_event(InputEvent.KEY_P)
    assert s2 == SceneState.PAUSED
    assert fsm.state.value == "PAUSED"
    assert sim.paused is True
    assert isinstance(fsm.active_scene, PausedScene)

    # Act & Assert (Step 4 — PAUSED -> SIMULATION on KEY_P and KEY_RETURN)
    s3 = fsm.handle_event(InputEvent.KEY_P)
    assert s3 == SceneState.SIMULATION
    assert sim.paused is False
    fsm.handle_event(InputEvent.KEY_P)
    assert fsm.state.value == "PAUSED"
    s4 = fsm.handle_event(InputEvent.KEY_RETURN)
    assert s4 == SceneState.SIMULATION
    assert sim.paused is False

    # Act & Assert (Step 5 — Any state -> QUIT on KEY_ESCAPE and QUIT_EVENT)
    s5 = fsm.handle_event(InputEvent.KEY_ESCAPE)
    assert s5 == SceneState.QUIT
    assert not fsm.is_running
    assert fsm.active_scene is None
    assert fsm.handle_event(InputEvent.KEY_RETURN) == SceneState.QUIT

    fsm_title = SceneFSM(SimulationState.create_default(asteroid_count=8, seed=42))
    assert fsm_title.handle_event(InputEvent.QUIT_EVENT) == SceneState.QUIT

    fsm_paused = SceneFSM(
        SimulationState.create_default(asteroid_count=8, seed=42),
        initial_state=SceneState.PAUSED,
    )
    assert fsm_paused.handle_event(InputEvent.QUIT_EVENT) == SceneState.QUIT


def test_scene_fsm_direction_reversal_and_speed_clamping() -> None:
    """Verify KEY_SPACE direction reversal and KEY_PLUS/KEY_MINUS clamping across states."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)
    fsm = SceneFSM(simulation=sim, initial_state=SceneState.SIMULATION)
    initial_jd = sim.julian_date
    initial_speed = sim.current_speed_days_per_sec

    # Act & Assert (Direction reversal in SIMULATION and PAUSED)
    fsm.handle_event(InputEvent.KEY_SPACE)
    assert sim.direction == -1
    assert sim.julian_date == initial_jd
    assert sim.current_speed_days_per_sec == initial_speed
    assert sim.effective_rate_days_per_sec == -initial_speed

    fsm.handle_event(InputEvent.KEY_P)
    fsm.handle_event(InputEvent.KEY_SPACE)
    assert fsm.state == SceneState.PAUSED
    assert sim.direction == 1
    assert sim.julian_date == initial_jd
    assert sim.effective_rate_days_per_sec == 0.0

    # Act & Assert (Speed ladder stepping and clamping in PAUSED and SIMULATION)
    for _ in range(25):
        fsm.handle_event(InputEvent.KEY_PLUS)
    assert fsm.state == SceneState.PAUSED
    assert sim.speed_index == len(SPEED_LADDER_DAYS_PER_SEC) - 1
    assert sim.current_speed_days_per_sec == SPEED_LADDER_DAYS_PER_SEC[-1] == 1826.25

    resumed_state = fsm.handle_event(InputEvent.KEY_RETURN)
    assert resumed_state == SceneState.SIMULATION
    assert fsm.current_state.value == "SIMULATION"
    assert sim.effective_rate_days_per_sec == 1826.25

    for _ in range(25):
        fsm.handle_event(InputEvent.KEY_MINUS)
    assert fsm.state.value == "SIMULATION"
    assert sim.speed_index == 0
    assert sim.current_speed_days_per_sec == SPEED_LADDER_DAYS_PER_SEC[0] == 0.01
    assert sim.effective_rate_days_per_sec == 0.01


def test_scene_fsm_update_advances_in_simulation_and_freezes_in_paused_title_quit() -> None:
    """Verify SceneFSM.update advances in SIMULATION and freezes in TITLE, PAUSED, and QUIT."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)
    fsm = SceneFSM(simulation=sim)
    jd0 = sim.julian_date
    earth0 = sim.cached_positions_au["Earth"]

    # Act & Assert (Freeze in TITLE)
    dt_title = fsm.update(0.05)
    assert dt_title == 0.0
    assert sim.julian_date == jd0
    assert sim.cached_positions_au["Earth"] == earth0

    # Act & Assert (Advance in SIMULATION)
    fsm.handle_event(InputEvent.KEY_RETURN)
    dt_sim = fsm.update(0.5)
    assert dt_sim == pytest.approx(0.5 * sim.current_speed_days_per_sec)
    assert sim.julian_date == pytest.approx(jd0 + dt_sim)
    jd_after_sim = sim.julian_date
    positions_after_sim = dict(sim.cached_positions_au)

    # Act & Assert (Freeze in PAUSED)
    fsm.handle_event(InputEvent.KEY_P)
    dt_paused = fsm.update(0.05)
    assert dt_paused == 0.0
    assert sim.julian_date == jd_after_sim
    assert sim.cached_positions_au == positions_after_sim

    # Act & Assert (Freeze in QUIT)
    fsm.handle_event(InputEvent.KEY_ESCAPE)
    dt_quit = fsm.update(0.05)
    assert dt_quit == 0.0
    assert sim.julian_date == jd_after_sim
    assert sim.cached_positions_au == positions_after_sim


def test_scene_fsm_frame_cycling_presets_zoom_reset_and_key_other_noop() -> None:
    """Verify frame cycling, presets 1..5, zoom, epoch reset, and KEY_OTHER in SIM and PAUSED."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=16, seed=42)
    fsm = SceneFSM(simulation=sim, initial_state=SceneState.SIMULATION)
    frame_names = tuple(sim.frames_by_name.keys())

    # Act & Assert (Reference frame cycling KEY_TAB / KEY_SHIFT_TAB in SIMULATION)
    fsm.handle_event(InputEvent.KEY_TAB)
    assert sim.active_frame_name == frame_names[1]
    fsm.handle_event(InputEvent.KEY_SHIFT_TAB)
    assert sim.active_frame_name == frame_names[0] == "Sun"
    fsm.handle_event(InputEvent.KEY_SHIFT_TAB)
    assert sim.active_frame_name == frame_names[-1]
    fsm.handle_event(InputEvent.KEY_TAB)
    assert sim.active_frame_name == "Sun"

    # Act & Assert (Scene presets KEY_DIGIT_1..5 and zoom KEY_LEFT_BRACKET / KEY_RIGHT_BRACKET)
    digit_presets = (
        (InputEvent.KEY_DIGIT_1, 1),
        (InputEvent.KEY_DIGIT_2, 2),
        (InputEvent.KEY_DIGIT_3, 3),
        (InputEvent.KEY_DIGIT_4, 4),
        (InputEvent.KEY_DIGIT_5, 5),
    )
    for digit_event, preset_id in digit_presets:
        assert fsm.handle_event(digit_event) == SceneState.SIMULATION
        assert sim.active_scene_id == preset_id

    fsm.handle_event(InputEvent.KEY_DIGIT_1)
    assert sim.zoom_multiplier == pytest.approx(1.0)
    fsm.handle_event(InputEvent.KEY_RIGHT_BRACKET)
    assert sim.zoom_multiplier == pytest.approx(ZOOM_IN_FACTOR)
    fsm.handle_event(InputEvent.KEY_LEFT_BRACKET)
    assert sim.zoom_multiplier == pytest.approx(ZOOM_IN_FACTOR * ZOOM_OUT_FACTOR)

    # Act & Assert (Epoch reset KEY_R and unrecognized KEY_OTHER in SIMULATION and PAUSED)
    fsm.handle_event(InputEvent.KEY_SPACE)
    fsm.update(2.0)
    assert sim.julian_date != sim.initial_jd
    assert sim.direction == -1
    fsm.handle_event(InputEvent.KEY_R)
    assert sim.julian_date == sim.initial_jd
    assert sim.direction == 1
    assert fsm.handle_event(InputEvent.KEY_OTHER) == SceneState.SIMULATION

    fsm.handle_event(InputEvent.KEY_P)
    assert fsm.state == SceneState.PAUSED
    fsm.handle_event(InputEvent.KEY_TAB)
    assert sim.active_frame_name == frame_names[1]
    assert fsm.state == SceneState.PAUSED
    fsm.handle_event(InputEvent.KEY_SHIFT_TAB)
    assert sim.active_frame_name == "Sun"
    assert fsm.state == SceneState.PAUSED
    fsm.handle_event(InputEvent.KEY_DIGIT_2)
    assert sim.active_scene_id == 2
    assert fsm.state == SceneState.PAUSED
    fsm.handle_event(InputEvent.KEY_DIGIT_1)
    fsm.handle_event(InputEvent.KEY_RIGHT_BRACKET)
    assert sim.zoom_multiplier == pytest.approx(ZOOM_IN_FACTOR)
    fsm.handle_event(InputEvent.KEY_LEFT_BRACKET)
    assert sim.zoom_multiplier == pytest.approx(ZOOM_IN_FACTOR * ZOOM_OUT_FACTOR)
    fsm.handle_event(InputEvent.KEY_R)
    assert sim.julian_date == sim.initial_jd
    assert fsm.handle_event(InputEvent.KEY_OTHER) == SceneState.PAUSED


def test_scene_fsm_custom_initial_state_and_validation_errors() -> None:
    """Verify default construction, custom initial_state pause sync, and ValueError guards."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=8, seed=42)

    # Act & Assert
    default_fsm = SceneFSM()
    assert default_fsm.state == SceneState.TITLE
    assert isinstance(default_fsm.simulation, SimulationState)

    paused_fsm = SceneFSM(simulation=sim, initial_state=SceneState.PAUSED)
    assert paused_fsm.state == SceneState.PAUSED
    assert sim.paused is True

    sim_unpaused = SceneFSM(simulation=sim, initial_state=SceneState.SIMULATION)
    assert sim_unpaused.state == SceneState.SIMULATION
    assert sim.paused is False

    bad_init_args: tuple[object, ...] = (sim, "INVALID")
    with pytest.raises(ValueError, match="initial_state"):
        SceneFSM(*bad_init_args)

    bad_event_args: tuple[object, ...] = ("NOT_AN_EVENT",)
    with pytest.raises(ValueError, match="event"):
        paused_fsm.handle_event(*bad_event_args)

    for invalid_dt in (-0.1, float("nan"), float("inf"), float("-inf"), True):
        with pytest.raises(ValueError, match="dt_wall_sec"):
            paused_fsm.update(invalid_dt)


def test_scenes_module_has_zero_pygame_imports() -> None:
    """Verify src/solar_system/scenes.py has zero pygame imports statically and at runtime."""
    # Arrange
    scenes_path = Path(__file__).resolve().parents[1] / "src" / "solar_system" / "scenes.py"
    source = scenes_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(scenes_path))

    # Act
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
    fsm = SceneFSM(
        simulation=SimulationState.create_default(asteroid_count=8, seed=42),
        initial_state=SceneState.SIMULATION,
    )
    delta_jd = fsm.update(0.25)

    # Assert
    for mod_name in imported_modules:
        assert not mod_name.startswith("pygame"), f"Forbidden pygame import found: {mod_name}"
    assert "pygame" not in sys.modules
    assert delta_jd > 0.0


def test_scenes_public_exports_in_solar_system_package() -> None:
    """Verify SceneState, InputEvent, TitleScene, SimulationScene, PausedScene, and SceneFSM exports."""
    # Arrange
    expected_exports = {
        "SceneState": SceneState,
        "InputEvent": InputEvent,
        "TitleScene": TitleScene,
        "SimulationScene": SimulationScene,
        "PausedScene": PausedScene,
        "SceneFSM": SceneFSM,
    }

    # Act & Assert
    for symbol_name, symbol_obj in expected_exports.items():
        assert symbol_name in solar_system.__all__
        assert getattr(solar_system, symbol_name) is symbol_obj