"""Pygame desktop window lifecycle, 60 FPS loop, and CLI entry point.

Provides :class:`GuiInitializationError`, :func:`init_window`,
:func:`translate_pygame_event`, :func:`capture_visual_proof_suite`,
:func:`run_app`, :func:`build_arg_parser`, and :func:`main` for launching the
interactive 1440x1080 solar system simulation or running the deterministic
7-stage visual-proof screenshot capture suite.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pygame

from solar_system.renderer import SolarSystemRenderer
from solar_system.scenes import InputEvent, SceneFSM, SceneState
from solar_system.simulation import SimulationState

__all__ = [
    "FIXED_CAPTURE_DT_SEC",
    "MAX_DT_WALL_SEC",
    "TARGET_FPS",
    "VISUAL_PROOF_FILENAMES",
    "WINDOW_HEIGHT",
    "WINDOW_TITLE",
    "WINDOW_WIDTH",
    "GuiInitializationError",
    "build_arg_parser",
    "capture_visual_proof_suite",
    "init_window",
    "main",
    "run_app",
    "translate_pygame_event",
]

WINDOW_WIDTH: int = 1440
WINDOW_HEIGHT: int = 1080
WINDOW_TITLE: str = "Favur - Solar System"
TARGET_FPS: int = 60
MAX_DT_WALL_SEC: float = 0.1
FIXED_CAPTURE_DT_SEC: float = 1.0 / 60.0
VISUAL_PROOF_FILENAMES: tuple[str, ...] = (
    "01_first_light.png",
    "02_title_scene.png",
    "03_simulation_scene.png",
    "04_paused_scene.png",
    "05_before_reversal.png",
    "06_after_reversal.png",
    "07_rate_change.png",
)


class GuiInitializationError(RuntimeError):
    """Raised when Pygame display, subsystem, or font initialization fails."""


def init_window(
    width: int = WINDOW_WIDTH,
    height: int = WINDOW_HEIGHT,
    title: str = WINDOW_TITLE,
) -> pygame.Surface:
    """Initialize Pygame subsystems and open a non-fullscreen desktop window.

    Args:
        width: Viewport width in pixels (must be positive).
        height: Viewport height in pixels (must be positive).
        title: Window caption string.

    Returns:
        Initialized :class:`pygame.Surface` representing the window display.

    Raises:
        ValueError: If ``width <= 0`` or ``height <= 0``.
        GuiInitializationError: If Pygame subsystem, font, or window creation fails.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers")

    try:
        init_result = pygame.init()
        if isinstance(init_result, tuple) and len(init_result) == 2:
            numpass, numfail = init_result
            if numpass <= 0:
                raise GuiInitializationError(
                    f"Pygame initialization failed (0 subsystems initialized, {numfail} failed)"
                )
        pygame.font.init()
        surface = pygame.display.set_mode((width, height), flags=0)
        if surface is None:
            raise GuiInitializationError("pygame.display.set_mode returned None")
        pygame.display.set_caption(title)
        return surface
    except (pygame.error, RuntimeError, OSError) as exc:
        if isinstance(exc, GuiInitializationError):
            raise
        raise GuiInitializationError(
            f"Failed to initialize {width}x{height} Pygame window '{title}': {exc}"
        ) from exc


def translate_pygame_event(event: pygame.event.Event) -> InputEvent | None:
    """Translate a Pygame event into a normalized headless :class:`InputEvent` token.

    Args:
        event: Pygame event object from :func:`pygame.event.get`.

    Returns:
        Normalized :class:`InputEvent` enum member, or ``None`` for non-quit/non-keydown
        events.
    """
    event_type = getattr(event, "type", None)
    if event_type == pygame.QUIT:
        return InputEvent.QUIT_EVENT
    if event_type != pygame.KEYDOWN:
        return None

    key = getattr(event, "key", None)
    mod = int(getattr(event, "mod", 0))

    if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return InputEvent.KEY_RETURN
    if key == pygame.K_SPACE:
        return InputEvent.KEY_SPACE
    if key == pygame.K_p:
        return InputEvent.KEY_P
    if key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
        return InputEvent.KEY_PLUS
    if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
        return InputEvent.KEY_MINUS
    if key == pygame.K_ESCAPE:
        return InputEvent.KEY_ESCAPE
    if key == pygame.K_r:
        return InputEvent.KEY_R
    if key == pygame.K_TAB:
        if (mod & pygame.KMOD_SHIFT) != 0:
            return InputEvent.KEY_SHIFT_TAB
        return InputEvent.KEY_TAB
    if key == pygame.K_1:
        return InputEvent.KEY_DIGIT_1
    if key == pygame.K_2:
        return InputEvent.KEY_DIGIT_2
    if key == pygame.K_3:
        return InputEvent.KEY_DIGIT_3
    if key == pygame.K_4:
        return InputEvent.KEY_DIGIT_4
    if key == pygame.K_5:
        return InputEvent.KEY_DIGIT_5
    if key == pygame.K_LEFTBRACKET:
        return InputEvent.KEY_LEFT_BRACKET
    if key == pygame.K_RIGHTBRACKET:
        return InputEvent.KEY_RIGHT_BRACKET
    return InputEvent.KEY_OTHER


def capture_visual_proof_suite(
    output_dir: str | Path,
    *,
    renderer: SolarSystemRenderer,
    fsm: SceneFSM,
    flip_display: bool = False,
) -> list[Path]:
    """Generate the 7 progressive 1440x1080 PNG visual-proof screenshots deterministically.

    Args:
        output_dir: Destination directory for ``01_first_light.png`` through ``07_rate_change.png``.
        renderer: Active :class:`SolarSystemRenderer` instance.
        fsm: Active :class:`SceneFSM` instance initialized at ``SceneState.TITLE``.
        flip_display: Whether to pump OS events and call :func:`pygame.display.flip` each frame.

    Returns:
        Ordered list of 7 written :class:`pathlib.Path` screenshot files.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    def _render_and_save(filename: str, *, show_first_light_only: bool = False) -> None:
        renderer.render_frame(
            fsm.simulation,
            scene_state=fsm.state,
            show_first_light_only=show_first_light_only,
        )
        if flip_display:
            pygame.display.flip()
        path = renderer.save_screenshot(out_dir / filename)
        saved_paths.append(path)

    def _step_frames(frame_count: int) -> None:
        for _ in range(frame_count):
            if flip_display:
                pygame.event.pump()
            fsm.update(FIXED_CAPTURE_DT_SEC)

    # Stage 1: 01_first_light.png (TITLE, JD 2451545.00, 2000-01-01, show_first_light_only=True)
    _render_and_save("01_first_light.png", show_first_light_only=True)

    # Stage 2: 02_title_scene.png (TITLE, JD 2451545.00, 2000-01-01, full HUD + title banner)
    _render_and_save("02_title_scene.png", show_first_light_only=False)

    # Stage 3: 03_simulation_scene.png (KEY_RETURN, KEY_PLUS x3 -> +10.00 d/s, 120 frames -> JD 2451565.00)
    fsm.handle_event(InputEvent.KEY_RETURN)
    for _ in range(3):
        fsm.handle_event(InputEvent.KEY_PLUS)
    _step_frames(120)
    _render_and_save("03_simulation_scene.png", show_first_light_only=False)

    # Stage 4: 04_paused_scene.png (KEY_P -> PAUSED, 15 frames -> frozen JD 2451565.00)
    fsm.handle_event(InputEvent.KEY_P)
    _step_frames(15)
    _render_and_save("04_paused_scene.png", show_first_light_only=False)

    # Stage 5: 05_before_reversal.png (KEY_P -> SIMULATION, 120 frames -> JD 2451585.00)
    fsm.handle_event(InputEvent.KEY_P)
    _step_frames(120)
    _render_and_save("05_before_reversal.png", show_first_light_only=False)

    # Stage 6: 06_after_reversal.png (KEY_SPACE -> REVERSE (-1), 60 frames -> JD 2451575.00)
    fsm.handle_event(InputEvent.KEY_SPACE)
    _step_frames(60)
    _render_and_save("06_after_reversal.png", show_first_light_only=False)

    # Stage 7: 07_rate_change.png (KEY_SPACE -> FORWARD (+1), KEY_PLUS x2 -> +90.00 d/s, 30 frames -> JD 2451620.00)
    fsm.handle_event(InputEvent.KEY_SPACE)
    for _ in range(2):
        fsm.handle_event(InputEvent.KEY_PLUS)
    _step_frames(30)
    _render_and_save("07_rate_change.png", show_first_light_only=False)

    return saved_paths


def run_app(
    max_frames: int | None = None,
    screenshot_schedule: dict[int, Path] | None = None,
    *,
    capture_visual_proof_dir: Path | None = None,
    surface: pygame.Surface | None = None,
) -> int:
    """Run the 60 FPS interactive simulation loop or deterministic visual-proof capture.

    Args:
        max_frames: Optional non-negative frame limit for automatic exit.
        screenshot_schedule: Optional mapping of zero-based frame index to PNG output path.
        capture_visual_proof_dir: Optional directory to write the 7-stage visual-proof suite.
        surface: Optional pre-created :class:`pygame.Surface` for offscreen testing.

    Returns:
        Exit code ``0`` on clean shutdown.

    Raises:
        ValueError: If ``max_frames`` is negative.
        GuiInitializationError: If window creation fails when ``surface`` is ``None``.
    """
    if max_frames is not None and max_frames < 0:
        raise ValueError("max_frames must be non-negative or None")

    owns_window = surface is None
    active_surface = (
        init_window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
        if owns_window
        else surface
    )
    assert active_surface is not None

    try:
        sim = SimulationState.create_default()
        fsm = SceneFSM(simulation=sim, initial_state=SceneState.TITLE)
        renderer = SolarSystemRenderer(surface=active_surface)

        if capture_visual_proof_dir is not None:
            capture_visual_proof_suite(
                capture_visual_proof_dir,
                renderer=renderer,
                fsm=fsm,
                flip_display=owns_window,
            )
            if max_frames is not None:
                return 0

        clock = pygame.time.Clock()
        frame_index: int = 0

        while fsm.is_running:
            if max_frames is not None and frame_index >= max_frames:
                break

            elapsed_ms = clock.tick(TARGET_FPS)
            dt_wall = min(max(elapsed_ms / 1000.0, 0.0), MAX_DT_WALL_SEC)

            for pg_event in pygame.event.get():
                mapped_event = translate_pygame_event(pg_event)
                if mapped_event is not None:
                    fsm.handle_event(mapped_event)
                    if not fsm.is_running:
                        break

            if not fsm.is_running:
                break

            fsm.update(dt_wall)
            renderer.render_frame(
                fsm.simulation,
                scene_state=fsm.state,
                show_first_light_only=False,
            )
            if owns_window:
                pygame.display.flip()

            if screenshot_schedule is not None and frame_index in screenshot_schedule:
                renderer.save_screenshot(screenshot_schedule[frame_index])

            frame_index += 1

        return 0
    finally:
        if owns_window:
            pygame.quit()


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser for ``solar-system``."""
    parser = argparse.ArgumentParser(
        prog="solar-system",
        description="Favur - Solar System 2D Keplerian Orrery",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Exit automatically after N rendered frames.",
    )
    parser.add_argument(
        "--capture-visual-proof",
        nargs="?",
        const="visual-proof",
        default=None,
        help=(
            "Run deterministic 7-screenshot visual-proof progression into DIR "
            "(default: visual-proof)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for the ``solar-system`` application.

    Args:
        argv: Optional sequence of CLI arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code ``0`` on success, or ``1`` if initialization or execution fails.
    """
    parser = build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        if args.max_frames is not None and args.max_frames < 0:
            raise ValueError("--max-frames must be a non-negative integer")
        capture_dir = (
            Path(args.capture_visual_proof)
            if args.capture_visual_proof is not None
            else None
        )
        return run_app(
            max_frames=args.max_frames,
            capture_visual_proof_dir=capture_dir,
        )
    except GuiInitializationError as exc:
        sys.stderr.write(f"ERROR: GUI initialization failed: {exc}\n")
        return 1
    except (pygame.error, ValueError, KeyError, RuntimeError, OSError) as exc:
        sys.stderr.write(f"ERROR: Solar System application failed: {exc}\n")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())