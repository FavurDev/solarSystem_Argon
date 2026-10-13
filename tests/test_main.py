"""Offscreen unit and integration tests for `solar_system.main` lifecycle and CLI.

Loads `pygame`, `solar_system.renderer`, and `solar_system.main` lazily inside
`offscreen_main_env` with a `try ... finally:` cleanup block so that
`tests/conftest.py`'s headless zero-pygame audit (`assert "pygame" not in sys.modules`)
passes even during the TDD red phase when `solar_system.main` does not yet exist.
"""

from __future__ import annotations

import importlib
import struct
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from solar_system.scenes import InputEvent, SceneFSM, SceneState
from solar_system.simulation import SimulationState


@pytest.fixture
def offscreen_main_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Any, Any]]:
    """Lazily load pygame and solar_system.main with dummy SDL drivers and full teardown."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pre_existing_pygame_keys = {
        key for key in sys.modules if key == "pygame" or key.startswith("pygame.")
    }
    preloaded_keys = set(sys.modules)
    pygame: Any = None
    try:
        pygame = importlib.import_module("pygame")
        importlib.import_module("solar_system.renderer")
        main_mod = importlib.import_module("solar_system.main")
        pygame.init()
        pygame.font.init()
        yield pygame, main_mod
    finally:
        if pygame is not None:
            pygame.quit()
        sys.modules.pop("solar_system.main", None)
        sys.modules.pop("solar_system.renderer", None)
        for mod_name in list(sys.modules):
            if (
                (mod_name == "pygame" or mod_name.startswith("pygame."))
                and mod_name not in pre_existing_pygame_keys
            ) or mod_name not in preloaded_keys:
                sys.modules.pop(mod_name, None)


def _assert_valid_png_1440x1080(path: Path) -> None:
    """Assert that `path` is a non-empty (> 10 KB) 1440x1080 PNG file."""
    assert path.is_file(), f"Expected PNG file at {path}"
    data = path.read_bytes()
    assert len(data) > 10_000, f"Expected PNG > 10 KB, got {len(data)} bytes at {path}"
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1440, 1080)


def test_translate_pygame_event_mapping(
    offscreen_main_env: tuple[Any, Any],
) -> None:
    """Verify translate_pygame_event maps all Pygame events to InputEvent tokens (AC-3)."""
    # Arrange
    pygame, main_mod = offscreen_main_env
    mapped_cases: list[tuple[Any, InputEvent | None]] = [
        (pygame.event.Event(pygame.QUIT), InputEvent.QUIT_EVENT),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0), InputEvent.KEY_RETURN),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP_ENTER, mod=0), InputEvent.KEY_RETURN),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0), InputEvent.KEY_SPACE),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0), InputEvent.KEY_P),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PLUS, mod=0), InputEvent.KEY_PLUS),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_EQUALS, mod=0), InputEvent.KEY_PLUS),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP_PLUS, mod=0), InputEvent.KEY_PLUS),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_MINUS, mod=0), InputEvent.KEY_MINUS),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP_MINUS, mod=0), InputEvent.KEY_MINUS),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0), InputEvent.KEY_ESCAPE),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r, mod=0), InputEvent.KEY_R),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0), InputEvent.KEY_TAB),
        (
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_SHIFT),
            InputEvent.KEY_SHIFT_TAB,
        ),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1, mod=0), InputEvent.KEY_DIGIT_1),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2, mod=0), InputEvent.KEY_DIGIT_2),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3, mod=0), InputEvent.KEY_DIGIT_3),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_4, mod=0), InputEvent.KEY_DIGIT_4),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_5, mod=0), InputEvent.KEY_DIGIT_5),
        (
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFTBRACKET, mod=0),
            InputEvent.KEY_LEFT_BRACKET,
        ),
        (
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHTBRACKET, mod=0),
            InputEvent.KEY_RIGHT_BRACKET,
        ),
        (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0), InputEvent.KEY_OTHER),
        (pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, mod=0), None),
        (pygame.event.Event(pygame.MOUSEMOTION, pos=(100, 100)), None),
    ]

    # Act
    actual_results = [main_mod.translate_pygame_event(ev) for ev, _ in mapped_cases]

    # Assert
    expected_results = [expected for _, expected in mapped_cases]
    assert actual_results == expected_results


def test_init_window_success_and_error_handling(
    offscreen_main_env: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify init_window opens 1440x1080 'Favur - Solar System', checks dims, and wraps errors."""
    # Arrange
    pygame, main_mod = offscreen_main_env
    fake_surface = pygame.Surface((1440, 1080))
    recorded_calls: dict[str, Any] = {}

    def _fake_set_mode(size: tuple[int, int], flags: int = 0) -> Any:
        recorded_calls["size"] = size
        recorded_calls["flags"] = flags
        return fake_surface

    def _fake_set_caption(title: str) -> None:
        recorded_calls["title"] = title

    monkeypatch.setattr(pygame.display, "set_mode", _fake_set_mode)
    monkeypatch.setattr(pygame.display, "set_caption", _fake_set_caption)

    # Act
    returned_surface = main_mod.init_window()

    # Assert
    assert returned_surface is fake_surface
    assert recorded_calls["size"] == (1440, 1080)
    assert recorded_calls["flags"] == 0
    assert recorded_calls["title"] == "Favur - Solar System"

    with pytest.raises(ValueError, match="width and height"):
        main_mod.init_window(0, 1080)

    with pytest.raises(ValueError, match="width and height"):
        main_mod.init_window(1440, -1)

    def _raise_pygame_error(size: tuple[int, int], flags: int = 0) -> Any:
        _ = (size, flags)
        raise pygame.error("No available video device")

    monkeypatch.setattr(pygame.display, "set_mode", _raise_pygame_error)
    with pytest.raises(main_mod.GuiInitializationError) as exc_info:
        main_mod.init_window(1440, 1080, "Favur - Solar System")
    assert "No available video device" in str(exc_info.value)
    assert "1440x1080" in str(exc_info.value)


def test_init_window_raises_gui_initialization_error_on_pygame_error(
    offscreen_main_env: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify init_window raises GuiInitializationError when pygame.display.set_mode fails."""
    # Arrange
    pygame, main_mod = offscreen_main_env

    def _raise_pygame_error(size: tuple[int, int], flags: int = 0) -> Any:
        _ = (size, flags)
        raise pygame.error("No available video device")

    monkeypatch.setattr(pygame.display, "set_mode", _raise_pygame_error)

    # Act / Assert
    with pytest.raises(main_mod.GuiInitializationError) as exc_info:
        main_mod.init_window(1440, 1080, "Favur - Solar System")
    assert "No available video device" in str(exc_info.value)
    assert "1440x1080" in str(exc_info.value)
    with pytest.raises(ValueError, match="width and height"):
        main_mod.init_window(-10, 1080)


def test_main_gui_init_error_handling_prints_stderr_and_returns_one(
    offscreen_main_env: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify main() catches GuiInitializationError and negative --max-frames with exit code 1."""
    # Arrange
    _, main_mod = offscreen_main_env

    def _fail_run_app(*args: Any, **kwargs: Any) -> int:
        _ = (args, kwargs)
        raise main_mod.GuiInitializationError("Display driver unavailable")

    monkeypatch.setattr(main_mod, "run_app", _fail_run_app)

    # Act
    exit_code = main_mod.main(["--max-frames", "5"])
    captured = capsys.readouterr()

    # Assert
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.startswith("ERROR:")
    assert "Display driver unavailable" in captured.err
    assert "Traceback" not in captured.err
    assert len(captured.err.strip().splitlines()) == 1

    neg_exit_code = main_mod.main(["--max-frames", "-1"])
    neg_captured = capsys.readouterr()
    assert neg_exit_code == 1
    assert neg_captured.out == ""
    assert neg_captured.err.startswith("ERROR:")
    assert "Traceback" not in neg_captured.err


def test_run_app_bounded_frames_and_screenshot_schedule(
    offscreen_main_env: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify run_app executes bounded frames, writes scheduled PNGs, and handles QUIT event."""
    # Arrange
    pygame, main_mod = offscreen_main_env
    offscreen_surface = pygame.Surface((1440, 1080))
    f0_path = tmp_path / "f0.png"
    f4_path = tmp_path / "f4.png"
    schedule = {0: f0_path, 4: f4_path}

    # Act
    rc = main_mod.run_app(
        max_frames=5,
        screenshot_schedule=schedule,
        surface=offscreen_surface,
    )

    # Assert
    assert rc == 0
    _assert_valid_png_1440x1080(f0_path)
    _assert_valid_png_1440x1080(f4_path)

    events_dispatched = False

    def _fake_event_get() -> list[Any]:
        nonlocal events_dispatched
        if not events_dispatched:
            events_dispatched = True
            return [pygame.event.Event(pygame.QUIT)]
        return []

    monkeypatch.setattr(pygame.event, "get", _fake_event_get)
    quit_rc = main_mod.run_app(max_frames=30, surface=offscreen_surface)
    assert quit_rc == 0
    assert events_dispatched is True


def test_capture_visual_proof_suite_offscreen_creates_seven_valid_pngs(
    offscreen_main_env: tuple[Any, Any],
    tmp_path: Path,
) -> None:
    """Verify capture_visual_proof_suite writes all 7 1440x1080 PNGs and advances FSM state."""
    # Arrange
    pygame, main_mod = offscreen_main_env
    renderer_mod = importlib.import_module("solar_system.renderer")
    offscreen_surface = pygame.Surface((1440, 1080))
    renderer = renderer_mod.SolarSystemRenderer(offscreen_surface)
    sim = SimulationState.create_default(asteroid_count=360, seed=42)
    fsm = SceneFSM(simulation=sim, initial_state=SceneState.TITLE)
    out_dir = tmp_path / "visual-proof"

    # Act
    saved_paths = main_mod.capture_visual_proof_suite(
        out_dir,
        renderer=renderer,
        fsm=fsm,
        flip_display=False,
    )

    # Assert
    assert len(saved_paths) == 7
    assert [path.name for path in saved_paths] == list(main_mod.VISUAL_PROOF_FILENAMES)
    for path in saved_paths:
        _assert_valid_png_1440x1080(path)
    assert fsm.state == SceneState.SIMULATION
    assert fsm.simulation.direction == 1
    assert fsm.simulation.speed_index == 8
    final_epoch_jd = getattr(fsm.simulation, "epoch_jd", fsm.simulation.julian_date)
    assert final_epoch_jd == pytest.approx(2451620.0)


def test_main_cli_capture_visual_proof_invokes_run_app(
    offscreen_main_env: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify main(['--capture-visual-proof', DIR, '--max-frames', '360']) forwards args."""
    # Arrange
    _, main_mod = offscreen_main_env
    captured_kwargs: dict[str, Any] = {}

    def _fake_run_app(
        max_frames: int | None = None,
        screenshot_schedule: dict[int, Path] | None = None,
        *,
        capture_visual_proof_dir: Path | None = None,
        surface: Any = None,
    ) -> int:
        captured_kwargs["max_frames"] = max_frames
        captured_kwargs["screenshot_schedule"] = screenshot_schedule
        captured_kwargs["capture_visual_proof_dir"] = capture_visual_proof_dir
        captured_kwargs["surface"] = surface
        return 0

    monkeypatch.setattr(main_mod, "run_app", _fake_run_app)

    # Act
    rc = main_mod.main(["--capture-visual-proof", str(tmp_path), "--max-frames", "360"])

    # Assert
    assert rc == 0
    assert captured_kwargs["max_frames"] == 360
    assert captured_kwargs["capture_visual_proof_dir"] == tmp_path