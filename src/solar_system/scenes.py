"""Pure-Python headless scene finite-state machine and input event vocabulary.

Provides ``SceneState``, ``InputEvent``, ``ZOOM_IN_FACTOR``, ``ZOOM_OUT_FACTOR``,
``TitleScene``, ``SimulationScene``, ``PausedScene``, and ``SceneFSM`` for
coordinating state transitions across ``TITLE``, ``SIMULATION``, ``PAUSED``, and
``QUIT`` while delegating orbital clock, speed ladder, time-reversal, reference
frame, scene preset, and zoom controls to ``SimulationState`` with zero ``pygame``
dependencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from solar_system.simulation import SimulationState

ZOOM_IN_FACTOR: float = 1.25
ZOOM_OUT_FACTOR: float = 0.8


class SceneState(str, Enum):
    """Finite-state machine states for the solar system application lifecycle."""

    TITLE = "TITLE"
    SIMULATION = "SIMULATION"
    PAUSED = "PAUSED"
    QUIT = "QUIT"


class InputEvent(str, Enum):
    """Normalized headless input event tokens decoupled from pygame key constants."""

    QUIT_EVENT = "QUIT_EVENT"
    KEY_RETURN = "KEY_RETURN"
    KEY_SPACE = "KEY_SPACE"
    KEY_P = "KEY_P"
    KEY_PLUS = "KEY_PLUS"
    KEY_MINUS = "KEY_MINUS"
    KEY_ESCAPE = "KEY_ESCAPE"
    KEY_R = "KEY_R"
    KEY_TAB = "KEY_TAB"
    KEY_SHIFT_TAB = "KEY_SHIFT_TAB"
    KEY_DIGIT_1 = "KEY_DIGIT_1"
    KEY_DIGIT_2 = "KEY_DIGIT_2"
    KEY_DIGIT_3 = "KEY_DIGIT_3"
    KEY_DIGIT_4 = "KEY_DIGIT_4"
    KEY_DIGIT_5 = "KEY_DIGIT_5"
    KEY_LEFT_BRACKET = "KEY_LEFT_BRACKET"
    KEY_RIGHT_BRACKET = "KEY_RIGHT_BRACKET"
    KEY_OTHER = "KEY_OTHER"


_DIGIT_EVENT_TO_PRESET: dict[InputEvent, int] = {
    InputEvent.KEY_DIGIT_1: 1,
    InputEvent.KEY_DIGIT_2: 2,
    InputEvent.KEY_DIGIT_3: 3,
    InputEvent.KEY_DIGIT_4: 4,
    InputEvent.KEY_DIGIT_5: 5,
}


def _validate_dt_wall_sec(dt_wall_sec: float) -> float:
    """Validate that ``dt_wall_sec`` is a finite non-negative float (rejecting booleans).

    Args:
        dt_wall_sec: Elapsed wall-clock time in seconds.

    Returns:
        Validated ``dt_wall_sec`` converted to ``float``.

    Raises:
        ValueError: If ``dt_wall_sec`` is a boolean, non-numeric, negative, or non-finite.
    """
    if (
        type(dt_wall_sec) is bool
        or type(dt_wall_sec) not in (int, float)
        or not math.isfinite(dt_wall_sec)
        or dt_wall_sec < 0.0
    ):
        raise ValueError(f"dt_wall_sec must be a finite non-negative number, got {dt_wall_sec!r}")
    return float(dt_wall_sec)


def _cycle_reference_frame(simulation: SimulationState, step: int) -> str:
    """Cycle the active reference frame on ``simulation`` by ``step`` modulo registered frames.

    Args:
        simulation: Active ``SimulationState`` instance to mutate.
        step: Signed index offset (``+1`` for forward, ``-1`` for reverse).

    Returns:
        Name of the newly activated reference frame.
    """
    frame_names = tuple(simulation.frames_by_name.keys())
    if not frame_names:
        return simulation.active_frame_name
    if simulation.active_frame_name in frame_names:
        current_index = frame_names.index(simulation.active_frame_name)
    else:
        current_index = 0
    next_index = (current_index + step) % len(frame_names)
    target_frame = frame_names[next_index]
    simulation.set_reference_frame(frame_name=target_frame)
    return target_frame


@dataclass(frozen=True, slots=True)
class TitleScene:
    """Stateless controller for the startup title screen (``SceneState.TITLE``).

    Attributes:
        state: Associated ``SceneState`` enum member (``SceneState.TITLE``).
    """

    state: SceneState = SceneState.TITLE

    def handle_event(self, simulation: SimulationState, event: InputEvent) -> SceneState:
        """Process a normalized ``InputEvent`` while in ``SceneState.TITLE``.

        Args:
            simulation: Active ``SimulationState`` instance.
            event: Normalized headless ``InputEvent`` token.

        Returns:
            Next ``SceneState`` after handling the event.
        """
        if event is InputEvent.KEY_RETURN:
            if simulation.paused:
                simulation.toggle_pause()
            return SceneState.SIMULATION
        if event is InputEvent.KEY_ESCAPE or event is InputEvent.QUIT_EVENT:
            return SceneState.QUIT
        return SceneState.TITLE

    def update(self, simulation: SimulationState, dt_wall_sec: float) -> float:
        """Validate ``dt_wall_sec`` and keep the simulation frozen during the title screen.

        Args:
            simulation: Active ``SimulationState`` instance (left unchanged).
            dt_wall_sec: Non-negative elapsed wall-clock seconds.

        Returns:
            ``0.0`` because orbital progression is frozen in ``SceneState.TITLE``.

        Raises:
            ValueError: If ``dt_wall_sec`` is negative, non-finite, or a boolean.
        """
        _validate_dt_wall_sec(dt_wall_sec)
        _ = simulation
        return 0.0


class SceneFSM:
    """Headless finite-state machine coordinating ``TITLE``, ``SIMULATION``, ``PAUSED``, and ``QUIT``.

    Synchronizes ``simulation.paused`` with the active ``SceneState`` and routes
    normalized ``InputEvent`` tokens and ``update(dt_wall_sec)`` calls to the
    active scene controller without any ``pygame`` dependency.

    Attributes:
        simulation: Active ``SimulationState`` managed by this state machine.
        title_scene: Stateless controller for ``SceneState.TITLE``.
        simulation_scene: Stateless controller for ``SceneState.SIMULATION``.
        paused_scene: Stateless controller for ``SceneState.PAUSED``.
    """

    def __init__(
        self,
        simulation: SimulationState | None = None,
        initial_state: SceneState = SceneState.TITLE,
    ) -> None:
        """Initialize the scene finite-state machine and synchronize ``simulation.paused``.

        Args:
            simulation: Optional ``SimulationState`` instance; defaults to
                ``SimulationState.create_default()`` when ``None``.
            initial_state: Starting ``SceneState`` (defaults to ``SceneState.TITLE``).

        Raises:
            ValueError: If ``initial_state`` is not a ``SceneState`` member.
        """
        if initial_state not in SceneState:
            raise ValueError(
                f"initial_state must be a SceneState enum member, got {initial_state!r}"
            )
        if simulation is None:
            self.simulation: SimulationState = SimulationState.create_default()
        else:
            self.simulation = simulation
        self.title_scene: TitleScene = TitleScene()
        self.simulation_scene: SimulationScene = SimulationScene()
        self.paused_scene: PausedScene = PausedScene()
        self._state: SceneState = initial_state
        self._sync_pause_flag_for_state(initial_state)

    def _sync_pause_flag_for_state(self, target_state: SceneState) -> None:
        """Synchronize ``self.simulation.paused`` idempotently with ``target_state``."""
        if (target_state is SceneState.SIMULATION and self.simulation.paused) or (
            target_state is SceneState.PAUSED and not self.simulation.paused
        ):
            self.simulation.toggle_pause()

    @property
    def state(self) -> SceneState:
        """Return the active ``SceneState``."""
        return self._state

    @property
    def current_state(self) -> SceneState:
        """Return the active ``SceneState`` (alias for ``state``)."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return ``True`` while the FSM has not entered ``SceneState.QUIT``."""
        return self._state is not SceneState.QUIT

    @property
    def active_scene(self) -> TitleScene | SimulationScene | PausedScene | None:
        """Return the scene controller for the active state, or ``None`` in ``QUIT``."""
        if self._state is SceneState.TITLE:
            return self.title_scene
        if self._state is SceneState.SIMULATION:
            return self.simulation_scene
        if self._state is SceneState.PAUSED:
            return self.paused_scene
        return None

    def handle_event(self, event: InputEvent) -> SceneState:
        """Dispatch ``event`` to the active scene controller and update the FSM state.

        Args:
            event: Normalized headless ``InputEvent`` token.

        Returns:
            Updated ``SceneState`` after handling the event.

        Raises:
            ValueError: If ``event`` is not an ``InputEvent`` member.
        """
        if event not in InputEvent:
            raise ValueError(f"event must be an InputEvent enum member, got {event!r}")
        if self._state is SceneState.QUIT:
            return SceneState.QUIT
        scene = self.active_scene
        if scene is None:
            return SceneState.QUIT
        next_state = scene.handle_event(simulation=self.simulation, event=event)
        self._state = next_state
        self._sync_pause_flag_for_state(next_state)
        return self._state

    def update(self, dt_wall_sec: float) -> float:
        """Advance the active scene by ``dt_wall_sec`` and return the Julian Date delta.

        Args:
            dt_wall_sec: Non-negative elapsed wall-clock seconds.

        Returns:
            Signed Julian Date delta in ``SceneState.SIMULATION``, or ``0.0`` in
            ``SceneState.TITLE``, ``SceneState.PAUSED``, and ``SceneState.QUIT``.

        Raises:
            ValueError: If ``dt_wall_sec`` is negative, non-finite, or a boolean.
        """
        validated_dt = _validate_dt_wall_sec(dt_wall_sec)
        scene = self.active_scene
        if scene is None:
            return 0.0
        return scene.update(simulation=self.simulation, dt_wall_sec=validated_dt)


@dataclass(frozen=True, slots=True)
class SimulationScene:
    """Stateless controller for active orbital progression (``SceneState.SIMULATION``).

    Attributes:
        state: Associated ``SceneState`` enum member (``SceneState.SIMULATION``).
    """

    state: SceneState = SceneState.SIMULATION

    def handle_event(self, simulation: SimulationState, event: InputEvent) -> SceneState:
        """Dispatch interactive keyboard controls to ``simulation`` in ``SIMULATION`` state.

        Args:
            simulation: Active ``SimulationState`` instance to mutate.
            event: Normalized headless ``InputEvent`` token.

        Returns:
            Next ``SceneState`` after handling the event.
        """
        if event is InputEvent.KEY_ESCAPE or event is InputEvent.QUIT_EVENT:
            return SceneState.QUIT
        if event is InputEvent.KEY_P:
            if not simulation.paused:
                simulation.toggle_pause()
            return SceneState.PAUSED
        if event is InputEvent.KEY_SPACE:
            simulation.reverse_direction()
            return SceneState.SIMULATION
        if event is InputEvent.KEY_PLUS:
            simulation.speed_up()
            return SceneState.SIMULATION
        if event is InputEvent.KEY_MINUS:
            simulation.slow_down()
            return SceneState.SIMULATION
        if event is InputEvent.KEY_R:
            simulation.reset_epoch()
            return SceneState.SIMULATION
        if event is InputEvent.KEY_TAB:
            _cycle_reference_frame(simulation=simulation, step=1)
            return SceneState.SIMULATION
        if event is InputEvent.KEY_SHIFT_TAB:
            _cycle_reference_frame(simulation=simulation, step=-1)
            return SceneState.SIMULATION
        if event in _DIGIT_EVENT_TO_PRESET:
            preset_id = _DIGIT_EVENT_TO_PRESET[event]
            simulation.apply_scene_preset(scene_id=preset_id)
            return SceneState.SIMULATION
        if event is InputEvent.KEY_LEFT_BRACKET:
            simulation.adjust_zoom(factor=ZOOM_OUT_FACTOR)
            return SceneState.SIMULATION
        if event is InputEvent.KEY_RIGHT_BRACKET:
            simulation.adjust_zoom(factor=ZOOM_IN_FACTOR)
            return SceneState.SIMULATION
        return SceneState.SIMULATION

    def update(self, simulation: SimulationState, dt_wall_sec: float) -> float:
        """Advance ``simulation`` by ``dt_wall_sec`` and return the signed Julian Date delta.

        Args:
            simulation: Active ``SimulationState`` instance to step.
            dt_wall_sec: Non-negative elapsed wall-clock seconds.

        Returns:
            Signed Julian Date delta (``simulation.julian_date - previous_jd``).

        Raises:
            ValueError: If ``dt_wall_sec`` is negative, non-finite, or a boolean.
        """
        validated_dt = _validate_dt_wall_sec(dt_wall_sec)
        previous_jd = simulation.julian_date
        simulation.step(dt_wall_sec=validated_dt)
        return simulation.julian_date - previous_jd


@dataclass(frozen=True, slots=True)
class PausedScene:
    """Stateless controller for the paused overlay state (``SceneState.PAUSED``).

    Attributes:
        state: Associated ``SceneState`` enum member (``SceneState.PAUSED``).
    """

    state: SceneState = SceneState.PAUSED

    def handle_event(self, simulation: SimulationState, event: InputEvent) -> SceneState:
        """Process resume, quit, and inspection controls while in ``SceneState.PAUSED``.

        Args:
            simulation: Active ``SimulationState`` instance to mutate.
            event: Normalized headless ``InputEvent`` token.

        Returns:
            Next ``SceneState`` after handling the event.
        """
        if event is InputEvent.KEY_ESCAPE or event is InputEvent.QUIT_EVENT:
            return SceneState.QUIT
        if event is InputEvent.KEY_P or event is InputEvent.KEY_RETURN:
            if simulation.paused:
                simulation.toggle_pause()
            return SceneState.PAUSED if simulation.paused else SceneState.SIMULATION
        if event is InputEvent.KEY_SPACE:
            simulation.reverse_direction()
            return SceneState.PAUSED
        if event is InputEvent.KEY_PLUS:
            simulation.speed_up()
            return SceneState.PAUSED
        if event is InputEvent.KEY_MINUS:
            simulation.slow_down()
            return SceneState.PAUSED
        if event is InputEvent.KEY_R:
            simulation.reset_epoch()
            return SceneState.PAUSED
        if event is InputEvent.KEY_TAB:
            _cycle_reference_frame(simulation=simulation, step=1)
            return SceneState.PAUSED
        if event is InputEvent.KEY_SHIFT_TAB:
            _cycle_reference_frame(simulation=simulation, step=-1)
            return SceneState.PAUSED
        if event in _DIGIT_EVENT_TO_PRESET:
            preset_id = _DIGIT_EVENT_TO_PRESET[event]
            simulation.apply_scene_preset(scene_id=preset_id)
            return SceneState.PAUSED
        if event is InputEvent.KEY_LEFT_BRACKET:
            simulation.adjust_zoom(factor=ZOOM_OUT_FACTOR)
            return SceneState.PAUSED
        if event is InputEvent.KEY_RIGHT_BRACKET:
            simulation.adjust_zoom(factor=ZOOM_IN_FACTOR)
            return SceneState.PAUSED
        return SceneState.PAUSED

    def update(self, simulation: SimulationState, dt_wall_sec: float) -> float:
        """Validate ``dt_wall_sec`` and keep the simulation frozen while paused.

        Args:
            simulation: Active ``SimulationState`` instance (left unchanged).
            dt_wall_sec: Non-negative elapsed wall-clock seconds.

        Returns:
            ``0.0`` because orbital progression is frozen in ``SceneState.PAUSED``.

        Raises:
            ValueError: If ``dt_wall_sec`` is negative, non-finite, or a boolean.
        """
        _validate_dt_wall_sec(dt_wall_sec)
        _ = simulation
        return 0.0