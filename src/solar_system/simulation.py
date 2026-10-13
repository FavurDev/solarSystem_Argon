"""Pure-Python headless simulation clock, time-reversal state machine, and control facade.

Provides ``SimulationState`` (aliased as ``Simulation``), speed ladder and zoom
bounds constants, and ``jd_to_iso_date`` for converting Julian Dates to ISO-8601
calendar date strings without any GUI or ``pygame`` dependencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from solar_system.bodies import J2000_EPOCH_JD, CelestialBody, build_catalog
from solar_system.frames import ReferenceFrame, build_frame_registry, world_positions
from solar_system.trail import DEFAULT_MAX_TRAIL_POINTS, TrailBuffer
from solar_system.vector import Vec3

SPEED_LADDER_DAYS_PER_SEC: tuple[float, ...] = (
    0.01,
    0.1,
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    30.0,
    90.0,
    365.25,
    1826.25,
)
DEFAULT_SPEED_INDEX: int = 3
MIN_ZOOM_MULTIPLIER: float = 0.1
MAX_ZOOM_MULTIPLIER: float = 50.0

_INTERNAL_SCENE_PRESETS: dict[int, tuple[str, float, bool, str | None]] = {
    1: ("Sun", 1.0, False, "Earth"),
    2: ("Sun", 0.15, False, "Saturn"),
    3: ("Earth", 18.0, False, "Moon"),
    4: ("Mars", 2.5, False, "Mars"),
    5: ("Sun", 0.55, True, "Jupiter"),
}


def jd_to_iso_date(jd: float) -> str:
    """Convert a Julian Date epoch to an ISO-8601 calendar date string (``YYYY-MM-DD``).

    Args:
        jd: Julian Date epoch (TT/TDB days). Must be finite.

    Returns:
        Calendar date formatted as ``YYYY-MM-DD`` where ``2451545.0`` maps to ``"2000-01-01"``.

    Raises:
        ValueError: If ``jd`` is NaN or infinite.
    """
    if not math.isfinite(jd):
        raise ValueError("jd must be a finite float")
    # IMPLEMENTATION DECISION: Add 1e-12 before floor relative to J2000_EPOCH_JD (2451545.0 = 2000-01-01).
    # Rationale: Guards against -1e-13 floating-point roundoff after reversible step sequences
    # while preserving floor semantics for fractional and negative day offsets.
    # Alternatives: Raw math.floor(jd - J2000_EPOCH_JD) without epsilon guard.
    day_offset = math.floor((jd - J2000_EPOCH_JD) + 1e-12)
    target_date = date(2000, 1, 1) + timedelta(days=day_offset)
    return target_date.isoformat()


@dataclass
class SimulationState:
    """Mutable headless state machine for orbital clock progression and camera controls.

    Evaluates 3D celestial positions as a pure analytical function of ``julian_date``
    and ``active_frame_name`` via ``world_positions``, guaranteeing exact bidirectional
    time-reversal invariance without numerical integration drift.
    """

    julian_date: float
    initial_jd: float
    speed_index: int
    direction: int
    paused: bool
    active_frame_name: str
    active_scene_id: int
    zoom_multiplier: float
    pan_offset_px: tuple[float, float]
    selected_body_name: str | None
    show_labels: bool
    show_trails: bool
    show_orbits: bool
    show_kirkwood: bool
    show_hud: bool
    bodies: tuple[CelestialBody, ...]
    bodies_by_name: dict[str, CelestialBody]
    frames_by_name: dict[str, ReferenceFrame]
    trails: dict[str, TrailBuffer]
    cached_positions_au: dict[str, Vec3]

    @classmethod
    def create_default(
        cls,
        asteroid_count: int = 360,
        seed: int = 42,
        initial_jd: float = J2000_EPOCH_JD,
        max_trail_points: int = DEFAULT_MAX_TRAIL_POINTS,
    ) -> SimulationState:
        """Create a default simulation initialized at ``initial_jd`` in the ``"Sun"`` frame.

        Args:
            asteroid_count: Number of main-belt asteroids to generate.
            seed: Deterministic PRNG seed for asteroid generation.
            initial_jd: Starting Julian Date epoch (defaults to ``J2000_EPOCH_JD``).
            max_trail_points: Maximum samples retained per non-asteroid ``TrailBuffer``.

        Returns:
            Initialized ``SimulationState`` instance.

        Raises:
            ValueError: If ``initial_jd`` is not finite, ``asteroid_count < 0``, or
                ``max_trail_points < 2``.
        """
        if not math.isfinite(initial_jd):
            raise ValueError("initial_jd must be a finite float")
        bodies = build_catalog(asteroid_count=asteroid_count, seed=seed)
        bodies_by_name: dict[str, CelestialBody] = {body.name: body for body in bodies}
        frames_by_name: dict[str, ReferenceFrame] = build_frame_registry()
        for body in bodies:
            if body.category != "asteroid" and body.name not in frames_by_name:
                frames_by_name[body.name] = ReferenceFrame(
                    name=body.name,
                    center_body_name=body.name,
                    description=f"{body.name}-centered reference frame",
                )
        initial_frame = "Sun"
        trails: dict[str, TrailBuffer] = {
            body.name: TrailBuffer(max_points=max_trail_points, frame_name=initial_frame)
            for body in bodies
            if body.category != "asteroid"
        }
        cached_positions_au = world_positions(
            frame_center_name=initial_frame,
            bodies_by_name=bodies_by_name,
            jd=float(initial_jd),
        )
        return cls(
            julian_date=float(initial_jd),
            initial_jd=float(initial_jd),
            speed_index=DEFAULT_SPEED_INDEX,
            direction=1,
            paused=False,
            active_frame_name=initial_frame,
            active_scene_id=1,
            zoom_multiplier=1.0,
            pan_offset_px=(0.0, 0.0),
            selected_body_name=None,
            show_labels=True,
            show_trails=True,
            show_orbits=True,
            show_kirkwood=False,
            show_hud=True,
            bodies=bodies,
            bodies_by_name=bodies_by_name,
            frames_by_name=frames_by_name,
            trails=trails,
            cached_positions_au=cached_positions_au,
        )

    @property
    def current_speed_days_per_sec(self) -> float:
        """Return the active simulation speed magnitude in days per wall-clock second."""
        return SPEED_LADDER_DAYS_PER_SEC[self.speed_index]

    @property
    def effective_rate_days_per_sec(self) -> float:
        """Return the signed effective time rate in days per second (``0.0`` when paused)."""
        if self.paused:
            return 0.0
        return self.current_speed_days_per_sec * float(self.direction)

    def state_at(
        self,
        jd: float,
        frame_name: str | None = None,
    ) -> dict[str, Vec3]:
        """Evaluate 3D positions of all bodies at ``jd`` without mutating simulation state.

        Args:
            jd: Julian Date epoch to evaluate. Must be finite.
            frame_name: Optional coordinate reference frame name. Defaults to
                ``self.active_frame_name``.

        Returns:
            Dictionary mapping each body name to its 3D position in AU relative to
            the target frame origin.

        Raises:
            ValueError: If ``jd`` is NaN or infinite.
            KeyError: If ``frame_name`` is not registered in ``self.frames_by_name``.
        """
        if not math.isfinite(jd):
            raise ValueError("jd must be a finite float")
        target_frame_name = self.active_frame_name if frame_name is None else frame_name
        if target_frame_name not in self.frames_by_name:
            raise KeyError(f"Unknown reference frame: {target_frame_name!r}")
        center_body_name = self.frames_by_name[target_frame_name].center_body_name
        return world_positions(
            frame_center_name=center_body_name,
            bodies_by_name=self.bodies_by_name,
            jd=float(jd),
        )

    def step(self, dt_wall_sec: float) -> dict[str, Vec3]:
        """Advance the simulation clock by ``dt_wall_sec`` and update positions and trails.

        Args:
            dt_wall_sec: Non-negative elapsed wall-clock seconds.

        Returns:
            Updated (or unchanged if paused/zero-dt) ``cached_positions_au`` dictionary.

        Raises:
            ValueError: If ``dt_wall_sec`` is negative or not finite.
        """
        if not math.isfinite(dt_wall_sec) or dt_wall_sec < 0.0:
            raise ValueError(
                f"dt_wall_sec must be a finite non-negative number, got {dt_wall_sec!r}"
            )
        if self.paused or dt_wall_sec == 0.0:
            return self.cached_positions_au
        delta_jd = float(dt_wall_sec) * self.current_speed_days_per_sec * float(self.direction)
        self.julian_date = self.julian_date + delta_jd
        center_body_name = self.frames_by_name[self.active_frame_name].center_body_name
        new_positions = world_positions(
            frame_center_name=center_body_name,
            bodies_by_name=self.bodies_by_name,
            jd=self.julian_date,
        )
        self.cached_positions_au = new_positions
        for body_name, trail_buffer in self.trails.items():
            pos = new_positions[body_name]
            trail_buffer.append(
                x_au=pos.x,
                y_au=pos.y,
                jd=self.julian_date,
                frame_name=self.active_frame_name,
            )
        return self.cached_positions_au

    def toggle_pause(self) -> bool:
        """Flip the ``paused`` flag and return the new paused state."""
        self.paused = not self.paused
        return self.paused

    def reverse_direction(self) -> int:
        """Flip the time progression direction between ``+1`` and ``-1`` and return it."""
        self.direction = -1 if self.direction >= 0 else 1
        return self.direction

    def speed_up(self) -> float:
        """Increment ``speed_index`` clamped to the upper ladder bound and return new speed."""
        max_index = len(SPEED_LADDER_DAYS_PER_SEC) - 1
        self.speed_index = min(self.speed_index + 1, max_index)
        return self.current_speed_days_per_sec

    def slow_down(self) -> float:
        """Decrement ``speed_index`` clamped to ``0`` and return new speed."""
        self.speed_index = max(self.speed_index - 1, 0)
        return self.current_speed_days_per_sec

    def reset_epoch(self) -> None:
        """Restore ``julian_date`` to ``initial_jd``, ``direction`` to ``+1``, and clear trails."""
        self.julian_date = self.initial_jd
        self.direction = 1
        for trail_buffer in self.trails.values():
            trail_buffer.clear()
        center_body_name = self.frames_by_name[self.active_frame_name].center_body_name
        self.cached_positions_au = world_positions(
            frame_center_name=center_body_name,
            bodies_by_name=self.bodies_by_name,
            jd=self.julian_date,
        )

    def set_reference_frame(self, frame_name: str) -> None:
        """Switch the active coordinate reference frame, clear trails, and recompute positions.

        Args:
            frame_name: Name of the reference frame in ``self.frames_by_name``.

        Raises:
            KeyError: If ``frame_name`` is not registered in ``self.frames_by_name``.
        """
        if frame_name not in self.frames_by_name:
            raise KeyError(f"Unknown reference frame: {frame_name!r}")
        self.active_frame_name = frame_name
        for body_name, old_buffer in list(self.trails.items()):
            old_buffer.clear()
            if old_buffer.frame_name != frame_name:
                self.trails[body_name] = TrailBuffer(
                    max_points=old_buffer.max_points,
                    frame_name=frame_name,
                )
        center_body_name = self.frames_by_name[frame_name].center_body_name
        self.cached_positions_au = world_positions(
            frame_center_name=center_body_name,
            bodies_by_name=self.bodies_by_name,
            jd=self.julian_date,
        )

    def apply_scene_preset(
        self,
        scene_id: int,
        *,
        frame_name: str | None = None,
        zoom_multiplier: float | None = None,
        show_kirkwood: bool | None = None,
        selected_body_name: str | None = None,
    ) -> None:
        """Apply a built-in scene preset (``1..5``) with optional keyword overrides.

        Args:
            scene_id: Preset identifier in ``{1, 2, 3, 4, 5}``.
            frame_name: Optional override for the coordinate reference frame.
            zoom_multiplier: Optional override for the viewport zoom multiplier.
            show_kirkwood: Optional override for the Kirkwood gap overlay flag.
            selected_body_name: Optional override for the selected body name.

        Raises:
            ValueError: If ``scene_id`` is not an int in ``1..5`` or ``zoom_multiplier``
                is non-positive/non-finite.
            KeyError: If the resolved ``frame_name`` or ``selected_body_name`` is unknown.
        """
        if isinstance(scene_id, bool) or scene_id not in _INTERNAL_SCENE_PRESETS:
            raise ValueError(f"scene_id must be an integer in 1..5, got {scene_id!r}")
        default_frame, default_zoom, default_kirkwood, default_selected = _INTERNAL_SCENE_PRESETS[
            scene_id
        ]
        resolved_frame = default_frame if frame_name is None else frame_name
        resolved_zoom = default_zoom if zoom_multiplier is None else float(zoom_multiplier)
        if not math.isfinite(resolved_zoom) or resolved_zoom <= 0.0:
            raise ValueError(
                f"zoom_multiplier must be a finite positive float, got {resolved_zoom!r}"
            )
        clamped_zoom = max(MIN_ZOOM_MULTIPLIER, min(MAX_ZOOM_MULTIPLIER, resolved_zoom))
        resolved_kirkwood = default_kirkwood if show_kirkwood is None else bool(show_kirkwood)
        resolved_selected = default_selected if selected_body_name is None else selected_body_name
        if resolved_selected is not None and resolved_selected not in self.bodies_by_name:
            raise KeyError(f"Unknown body name: {resolved_selected!r}")
        self.set_reference_frame(frame_name=resolved_frame)
        self.active_scene_id = scene_id
        self.pan_offset_px = (0.0, 0.0)
        self.zoom_multiplier = clamped_zoom
        self.show_kirkwood = resolved_kirkwood
        self.selected_body_name = resolved_selected

    def select_body(self, body_name: str | None) -> None:
        """Select a celestial body for HUD inspection or pass ``None`` to clear selection.

        Args:
            body_name: Name of a body in ``self.bodies_by_name`` or ``None``.

        Raises:
            KeyError: If ``body_name`` is not ``None`` and not in ``self.bodies_by_name``.
        """
        if body_name is not None and body_name not in self.bodies_by_name:
            raise KeyError(f"Unknown body name: {body_name!r}")
        self.selected_body_name = body_name

    def adjust_zoom(self, factor: float) -> float:
        """Multiply ``zoom_multiplier`` by ``factor`` clamped to ``[0.1, 50.0]``.

        Args:
            factor: Positive finite zoom scale factor.

        Returns:
            Clamped ``zoom_multiplier``.

        Raises:
            ValueError: If ``factor`` is non-positive or not finite.
        """
        if not math.isfinite(factor) or factor <= 0.0:
            raise ValueError(f"Zoom factor must be a finite positive number, got {factor!r}")
        raw_zoom = self.zoom_multiplier * float(factor)
        self.zoom_multiplier = max(MIN_ZOOM_MULTIPLIER, min(MAX_ZOOM_MULTIPLIER, raw_zoom))
        return self.zoom_multiplier

    def pan_by_pixels(self, dx_px: float, dy_px: float) -> tuple[float, float]:
        """Accumulate pixel pan offset ``(dx_px, dy_px)`` onto ``pan_offset_px``.

        Args:
            dx_px: Horizontal pan delta in screen pixels. Must be finite.
            dy_px: Vertical pan delta in screen pixels. Must be finite.

        Returns:
            Updated ``(x_px, y_px)`` tuple.

        Raises:
            ValueError: If ``dx_px`` or ``dy_px`` is not finite.
        """
        if not (math.isfinite(dx_px) and math.isfinite(dy_px)):
            raise ValueError("Pan offsets dx_px and dy_px must be finite floats")
        cur_x, cur_y = self.pan_offset_px
        self.pan_offset_px = (cur_x + float(dx_px), cur_y + float(dy_px))
        return self.pan_offset_px


Simulation = SimulationState

__all__ = [
    "DEFAULT_SPEED_INDEX",
    "MAX_ZOOM_MULTIPLIER",
    "MIN_ZOOM_MULTIPLIER",
    "SPEED_LADDER_DAYS_PER_SEC",
    "Simulation",
    "SimulationState",
    "jd_to_iso_date",
]
