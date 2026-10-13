"""Pygame 2D scientific visualization renderer for the Solar System simulation.

Provides :class:`SolarSystemRenderer`, which renders all 8 visual layers back-to-front
onto a target :class:`pygame.Surface` using pre-allocated ``pygame.SRCALPHA`` overlay
surfaces to satisfy zero per-frame surface allocation (TD-003).
"""

from __future__ import annotations

import logging
import math
import random
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from solar_system.bodies import KIRKWOOD_GAPS, CelestialBody
from solar_system.scaling import (
    DEFAULT_DISPLAY_SCALE_CONFIG,
    DisplayScaleConfig,
    body_display_radius_px,
    heliocentric_distance_to_px,
    moon_distance_to_px,
    sample_orbit_screen_points,
    world_to_screen,
)
from solar_system.scenes import SceneFSM, SceneState
from solar_system.simulation import SimulationState, jd_to_iso_date
from solar_system.vector import Vec3

if TYPE_CHECKING:
    from solar_system.trail import TrailBuffer

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "BACKDROP_RGB",
    "DIRECTION_FORWARD_RGB",
    "DIRECTION_REVERSE_RGB",
    "HUD_PANEL_RGBA",
    "KIRKWOOD_LABEL_RGB",
    "KIRKWOOD_RING_RGB",
    "MODAL_BACKDROP_RGBA",
    "MODAL_BORDER_RGBA",
    "STARFIELD_COUNT",
    "STARFIELD_SEED",
    "SUN_CORE_RADIUS_PX",
    "SUN_CORE_RGB",
    "SUN_GLOW_RADIUS_PX",
    "SUN_GLOW_RGB",
    "SolarSystemRenderer",
]

# Deep-space backdrop and deterministic starfield constants
BACKDROP_RGB: tuple[int, int, int] = (6, 8, 20)
STARFIELD_SEED: int = 104729
STARFIELD_COUNT: int = 250

# Solar disk and corona palette
SUN_GLOW_RGB: tuple[int, int, int] = (255, 228, 132)
SUN_GLOW_RADIUS_PX: int = 22
SUN_CORE_RGB: tuple[int, int, int] = (255, 204, 51)
SUN_CORE_RADIUS_PX: int = 18

# Kirkwood resonance ring and HUD telemetry palette
KIRKWOOD_RING_RGB: tuple[int, int, int] = (80, 95, 135)
KIRKWOOD_LABEL_RGB: tuple[int, int, int] = (140, 160, 205)
HUD_PANEL_RGBA: tuple[int, int, int, int] = (14, 18, 38, 205)
DIRECTION_FORWARD_RGB: tuple[int, int, int] = (74, 222, 128)
DIRECTION_REVERSE_RGB: tuple[int, int, int] = (251, 191, 36)
MODAL_BACKDROP_RGBA: tuple[int, int, int, int] = (8, 12, 28, 190)
MODAL_BORDER_RGBA: tuple[int, int, int, int] = (110, 145, 220, 220)


class SolarSystemRenderer:
    """2D Pygame scientific visualization renderer for the Solar System simulation.

    Pre-allocates ``_trail_surface`` and ``_overlay_surface`` with ``pygame.SRCALPHA``
    at initialization so ``render_frame`` and ``draw`` perform zero per-frame surface
    allocations (TD-003).
    """

    def __init__(
        self,
        surface: pygame.Surface,
        scale_config: DisplayScaleConfig = DEFAULT_DISPLAY_SCALE_CONFIG,
    ) -> None:
        """Initialize the renderer and pre-allocate alpha compositing surfaces.

        Args:
            surface: Target Pygame display or offscreen surface to render onto.
            scale_config: Hierarchical logarithmic radial scaling configuration.

        Raises:
            ValueError: If ``surface`` is ``None`` or not a :class:`pygame.Surface`.
        """
        if surface is None or not isinstance(surface, pygame.Surface):
            raise ValueError("surface must be a valid pygame.Surface instance.")

        self._surface: pygame.Surface = surface
        self._scale_config: DisplayScaleConfig = scale_config

        width, height = surface.get_size()
        # IMPLEMENTATION DECISION: Pre-allocate SRCALPHA surfaces once at init.
        # Rationale: Avoids GC pressure and satisfies TD-003 zero per-frame Surface allocation.
        # Alternatives: Allocating per-trail surfaces each frame (rejected due to TD-003).
        self._trail_surface: pygame.Surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._overlay_surface: pygame.Surface = pygame.Surface((width, height), pygame.SRCALPHA)

        rng = random.Random(STARFIELD_SEED)
        self._stars: tuple[tuple[int, int, int, tuple[int, int, int]], ...] = tuple(
            (
                rng.randint(0, max(0, width - 1)),
                rng.randint(0, max(0, height - 1)),
                1 if rng.random() < 0.82 else 2,
                (b := rng.randint(135, 240), b, min(255, b + 15)),
            )
            for _ in range(STARFIELD_COUNT)
        )

        if not pygame.font.get_init():
            pygame.font.init()
        self._font_small: pygame.font.Font = self._load_font(13, bold=False)
        self._font_hud: pygame.font.Font = self._load_font(15, bold=False)
        self._font_title: pygame.font.Font = self._load_font(28, bold=True)
        _LOGGER.debug("Initialized SolarSystemRenderer (%dx%d).", width, height)

    @staticmethod
    def _load_font(size: int, *, bold: bool = False) -> pygame.font.Font:
        """Load a monospace font with safe fallback to the default Pygame font."""
        try:
            return pygame.font.SysFont("consolas", size, bold=bold)
        except pygame.error as exc:  # pragma: no cover - defensive fallback for minimal SDL builds
            _LOGGER.debug("SysFont fallback to default font: %s", exc)
            return pygame.font.Font(None, size + 4)

    @property
    def surface(self) -> pygame.Surface:
        """Return the target Pygame surface."""
        return self._surface

    @property
    def scale_config(self) -> DisplayScaleConfig:
        """Return the active display scaling configuration."""
        return self._scale_config

    def _effective_scale_config(self, sim: SimulationState) -> DisplayScaleConfig:
        """Compute camera-adjusted DisplayScaleConfig applying pan and zoom."""
        base_cx, base_cy = self._scale_config.sun_center
        pan_dx, pan_dy = sim.pan_offset_px
        zoom = max(0.05, float(sim.zoom_multiplier))
        return DisplayScaleConfig(
            viewport_width=self._scale_config.viewport_width,
            viewport_height=self._scale_config.viewport_height,
            sun_center=(round(base_cx + pan_dx), round(base_cy + pan_dy)),
            r_min_au=self._scale_config.r_min_au,
            r_max_au=self._scale_config.r_max_au,
            px_min=self._scale_config.px_min * zoom,
            px_max=self._scale_config.px_max * zoom,
            moon_r_min_au=self._scale_config.moon_r_min_au,
            moon_r_max_au=self._scale_config.moon_r_max_au,
            moon_px_min=self._scale_config.moon_px_min * zoom,
            moon_px_max=self._scale_config.moon_px_max * zoom,
        )

    def render_frame(
        self,
        simulation: SimulationState | SceneFSM,
        scene_state: SceneState | None = None,
        *,
        show_first_light_only: bool = False,
    ) -> None:
        """Render a complete 8-layer frame onto ``self._surface``.

        Args:
            simulation: Either a :class:`SimulationState` or a :class:`SceneFSM` wrapping it.
            scene_state: Explicit :class:`SceneState` override; defaults to ``simulation.state``
                when given a :class:`SceneFSM` or :attr:`SceneState.SIMULATION`.
            show_first_light_only: If ``True``, suppress orbit ellipses, trails, Kirkwood
                rings, labels, HUD, and modal overlays to render the clean First Light frame.
        """
        if isinstance(simulation, SceneFSM):
            sim = simulation.simulation
            active_scene = simulation.state if scene_state is None else scene_state
        else:
            sim = simulation
            active_scene = SceneState.SIMULATION if scene_state is None else scene_state

        cfg = self._effective_scale_config(sim)
        bodies_map = sim.bodies_by_name
        positions_map = sim.cached_positions_au
        trails_map = sim.trails

        # Layer 1: Deep-space backdrop and deterministic starfield
        self._draw_backdrop()

        # Layer 2: Kirkwood resonance gaps and main-belt asteroid field
        self._draw_asteroid_belt_and_kirkwood(
            sim=sim,
            cfg=cfg,
            bodies_map=bodies_map,
            positions_map=positions_map,
            show_first_light_only=show_first_light_only,
        )

        # Layer 3: Heliocentric static orbital paths (including First Light per MAC-1)
        if sim.show_orbits:
            self._draw_heliocentric_orbits(cfg=cfg, bodies_map=bodies_map)

        # Layer 4: Fading historical trajectory polylines on pre-allocated _trail_surface
        if sim.show_trails and not show_first_light_only:
            self._draw_fading_trails(
                cfg=cfg,
                bodies_map=bodies_map,
                trails_map=trails_map,
            )

        # Layer 5: Central Sun, planets, dwarf planets, comets, and Saturn rings
        planet_screen_coords = self._draw_sun_and_primary_bodies(
            sim=sim,
            cfg=cfg,
            bodies_map=bodies_map,
            positions_map=positions_map,
            show_first_light_only=show_first_light_only,
        )

        # Layer 6: Bounded moon neighborhoods around parent planets
        self._draw_moons(
            sim=sim,
            cfg=cfg,
            bodies_map=bodies_map,
            positions_map=positions_map,
            planet_screen_coords=planet_screen_coords,
            show_first_light_only=show_first_light_only,
        )

        # Layer 7: Semi-transparent HUD telemetry panel and controls legend
        if sim.show_hud and not show_first_light_only:
            self._draw_hud(sim=sim, active_scene=active_scene)

        # Layer 8: Scene modal overlays (TITLE and PAUSED banners)
        if not show_first_light_only and active_scene in (SceneState.TITLE, SceneState.PAUSED):
            self._draw_scene_overlay(active_scene=active_scene)

    def draw(
        self,
        fsm: SceneFSM | SimulationState,
        scene_state: SceneState | None = None,
        *,
        show_first_light_only: bool = False,
    ) -> None:
        """Render the current scene state from a :class:`SceneFSM` or :class:`SimulationState`.

        Args:
            fsm: Active :class:`SceneFSM` or :class:`SimulationState` instance to render.
            scene_state: Optional explicit :class:`SceneState` override.
            show_first_light_only: If ``True``, suppress orbit ellipses, trails, Kirkwood
                rings, labels, HUD, and modal overlays to render the clean First Light frame.
        """
        self.render_frame(
            fsm,
            scene_state=scene_state,
            show_first_light_only=show_first_light_only,
        )

    def save_screenshot(self, path: str | Path) -> Path:
        """Save the current surface buffer as an image file on disk.

        Args:
            path: Destination file path for the PNG screenshot.

        Returns:
            Resolved :class:`pathlib.Path` of the written image file.
        """
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self._surface, str(out_path))
        return out_path.resolve()

    def _draw_backdrop(self) -> None:
        """Render Layer 1: deep-space backdrop fill and 250 deterministic stars."""
        self._surface.fill(BACKDROP_RGB)
        for sx, sy, radius, color in self._stars:
            if radius <= 1:
                self._surface.set_at((sx, sy), color)
            else:
                pygame.draw.circle(self._surface, color, (sx, sy), radius)

    def _draw_asteroid_belt_and_kirkwood(
        self,
        *,
        sim: SimulationState,
        cfg: DisplayScaleConfig,
        bodies_map: dict[str, CelestialBody],
        positions_map: dict[str, Vec3],
        show_first_light_only: bool,
    ) -> None:
        """Render Layer 2: Kirkwood resonance gap rings and main-belt asteroid dots."""
        cx = round(cfg.sun_center[0])
        cy = round(cfg.sun_center[1])

        if sim.show_kirkwood and not show_first_light_only:
            for idx, gap in enumerate(KIRKWOOD_GAPS):
                gap_radius_px = round(heliocentric_distance_to_px(gap.center_au, cfg))
                if gap_radius_px > 2:
                    pygame.draw.circle(self._surface, KIRKWOOD_RING_RGB, (cx, cy), gap_radius_px, 1)
                    angle_rad = -0.55 + idx * 0.23
                    lx = cx + round(gap_radius_px * math.cos(angle_rad)) + 4
                    ly = cy + round(gap_radius_px * math.sin(angle_rad)) - 8
                    label_surf = self._font_small.render(gap.label, True, KIRKWOOD_LABEL_RGB)
                    self._surface.blit(label_surf, (lx, ly))

        for name, body in bodies_map.items():
            if body.category != "asteroid":
                continue
            pos_au = positions_map.get(name)
            if pos_au is None:
                continue
            ax, ay = world_to_screen(pos_au, cfg, parent_screen_pos=None, is_moon=False)
            radius_px = body_display_radius_px(body.radius_km, body.category)
            if radius_px <= 1:
                self._surface.set_at((ax, ay), body.style.color_rgb)
            else:
                pygame.draw.circle(self._surface, body.style.color_rgb, (ax, ay), radius_px)

    def _draw_heliocentric_orbits(
        self,
        *,
        cfg: DisplayScaleConfig,
        bodies_map: dict[str, CelestialBody],
    ) -> None:
        """Render Layer 3: static 180-vertex closed orbit ellipses for primary bodies."""
        for body in bodies_map.values():
            if body.category not in ("planet", "dwarf", "comet") or body.elements is None:
                continue
            orbit_pts = sample_orbit_screen_points(
                body.elements,
                parent_screen_pos=cfg.sun_center,
                is_moon=False,
                cfg=cfg,
                num_samples=180,
            )
            if len(orbit_pts) >= 3:
                pygame.draw.aalines(self._surface, body.style.trail_color_rgb, True, orbit_pts)

    def _draw_fading_trails(
        self,
        *,
        cfg: DisplayScaleConfig,
        bodies_map: dict[str, CelestialBody],
        trails_map: dict[str, TrailBuffer],
    ) -> None:
        """Render Layer 4: age-weighted fading historical trails on pre-allocated _trail_surface."""
        self._trail_surface.fill((0, 0, 0, 0))
        any_drawn = False

        for name, trail_buf in trails_map.items():
            if len(trail_buf) < 2:
                continue
            body = bodies_map.get(name)
            if body is None or body.category == "asteroid":
                continue

            pts = trail_buf.points()
            total = len(pts)
            tr, tg, tb = body.style.trail_color_rgb

            if body.category == "moon" and body.parent_name is not None:
                parent_trail = trails_map.get(body.parent_name)
                parent_pts = parent_trail.points() if parent_trail is not None else ()
                screen_pts: list[tuple[int, int]] = []
                for idx, pt in enumerate(pts):
                    if idx < len(parent_pts):
                        p_vec = Vec3(parent_pts[idx].x_au, parent_pts[idx].y_au, 0.0)
                    else:
                        p_vec = Vec3(0.0, 0.0, 0.0)
                    p_sx, p_sy = world_to_screen(p_vec, cfg, parent_screen_pos=None, is_moon=False)
                    rel_vec = Vec3(pt.x_au - p_vec.x, pt.y_au - p_vec.y, 0.0)
                    sx, sy = world_to_screen(
                        rel_vec,
                        cfg,
                        parent_screen_pos=(p_sx, p_sy),
                        is_moon=True,
                    )
                    screen_pts.append((sx, sy))
            else:
                screen_pts = [
                    world_to_screen(
                        (pt.x_au, pt.y_au),
                        cfg,
                        parent_screen_pos=None,
                        is_moon=False,
                    )
                    for pt in pts
                ]

            for idx in range(total - 1):
                p0 = screen_pts[idx]
                p1 = screen_pts[idx + 1]
                alpha = max(18, min(230, int(220 * (idx + 1) / total)))
                pygame.draw.line(self._trail_surface, (tr, tg, tb, alpha), p0, p1, 2)
                any_drawn = True

        if any_drawn:
            self._surface.blit(self._trail_surface, (0, 0))

    def _draw_sun_and_primary_bodies(
        self,
        *,
        sim: SimulationState,
        cfg: DisplayScaleConfig,
        bodies_map: dict[str, CelestialBody],
        positions_map: dict[str, Vec3],
        show_first_light_only: bool,
    ) -> dict[str, tuple[int, int]]:
        """Render Layer 5: Sun corona/core, planets, dwarf planets, comets, and rings."""
        cx, cy = cfg.sun_center

        pygame.draw.circle(self._surface, SUN_GLOW_RGB, (cx, cy), SUN_GLOW_RADIUS_PX)
        pygame.draw.circle(self._surface, SUN_CORE_RGB, (cx, cy), SUN_CORE_RADIUS_PX)

        planet_screen_coords: dict[str, tuple[int, int]] = {"Sun": cfg.sun_center}

        for name, body in bodies_map.items():
            if body.category not in ("planet", "dwarf", "comet"):
                continue
            pos_au = positions_map.get(name)
            if pos_au is None:
                continue

            ibx, iby = world_to_screen(pos_au, cfg, parent_screen_pos=None, is_moon=False)
            planet_screen_coords[name] = (ibx, iby)
            radius_px = body_display_radius_px(body.radius_km, body.category)

            if body.style.has_rings:
                ring_rx = max(radius_px + 7, round(radius_px * body.style.ring_outer_mult))
                ring_ry = max(4, round(radius_px * 0.72))
                ring_rect = pygame.Rect(ibx - ring_rx, iby - ring_ry, 2 * ring_rx, 2 * ring_ry)
                pygame.draw.ellipse(self._surface, body.style.trail_color_rgb, ring_rect, 2)

            pygame.draw.circle(self._surface, body.style.color_rgb, (ibx, iby), radius_px)

            if sim.show_labels and not show_first_light_only:
                label_surf = self._font_small.render(body.name, True, body.style.color_rgb)
                self._surface.blit(label_surf, (ibx + radius_px + 5, iby - 7))

        return planet_screen_coords

    def _draw_moons(
        self,
        *,
        sim: SimulationState,
        cfg: DisplayScaleConfig,
        bodies_map: dict[str, CelestialBody],
        positions_map: dict[str, Vec3],
        planet_screen_coords: dict[str, tuple[int, int]],
        show_first_light_only: bool,
    ) -> None:
        """Render Layer 6: bounded moon neighborhood orbits, moon disks, and labels."""
        for name, body in bodies_map.items():
            if body.category != "moon" or body.parent_name is None:
                continue
            parent_px = planet_screen_coords.get(body.parent_name)
            parent_pos_au = positions_map.get(body.parent_name)
            moon_pos_au = positions_map.get(name)
            if parent_px is None or parent_pos_au is None or moon_pos_au is None:
                continue

            if sim.show_orbits and not show_first_light_only and body.elements is not None:
                moon_orbit_r = round(moon_distance_to_px(body.elements.semi_major_axis_au, cfg))
                if moon_orbit_r >= 4:
                    pygame.draw.circle(
                        self._surface,
                        body.style.trail_color_rgb,
                        parent_px,
                        moon_orbit_r,
                        1,
                    )

            rel_vec_au = moon_pos_au - parent_pos_au
            mx, my = world_to_screen(rel_vec_au, cfg, parent_screen_pos=parent_px, is_moon=True)
            m_radius_px = body_display_radius_px(body.radius_km, "moon")
            pygame.draw.circle(self._surface, body.style.color_rgb, (mx, my), m_radius_px)

            if sim.show_labels and not show_first_light_only:
                m_label = self._font_small.render(body.name, True, body.style.color_rgb)
                self._surface.blit(m_label, (mx + m_radius_px + 3, my - 6))

    def _draw_hud(self, *, sim: SimulationState, active_scene: SceneState) -> None:
        """Render Layer 7: semi-transparent HUD telemetry panel and bottom-left controls legend."""
        self._overlay_surface.fill((0, 0, 0, 0))
        panel_rect = pygame.Rect(16, 16, 360, 178)
        pygame.draw.rect(self._overlay_surface, HUD_PANEL_RGBA, panel_rect, border_radius=8)
        pygame.draw.rect(
            self._overlay_surface,
            MODAL_BORDER_RGBA,
            panel_rect,
            width=1,
            border_radius=8,
        )
        self._surface.blit(self._overlay_surface, (0, 0))

        iso_date = jd_to_iso_date(sim.julian_date)
        elapsed_days = sim.julian_date - sim.initial_jd
        elapsed_years = elapsed_days / 365.25
        dir_sign = int(sim.direction)
        dir_text = "FORWARD (+1)" if dir_sign >= 0 else "REVERSE (-1)"
        dir_color = DIRECTION_FORWARD_RGB if dir_sign >= 0 else DIRECTION_REVERSE_RGB
        signed_rate = sim.current_speed_days_per_sec * (1.0 if dir_sign >= 0 else -1.0)

        hud_lines: list[tuple[str, tuple[int, int, int]]] = [
            (f"Epoch: {iso_date} (JD {sim.julian_date:.2f})", (235, 240, 255)),
            (f"Elapsed: {elapsed_days:+.1f} d ({elapsed_years:+.2f} yr)", (205, 215, 240)),
            (f"Direction: {dir_text}", dir_color),
            (f"Rate: {signed_rate:+.2f} d/s", dir_color),
            (f"Scene: {active_scene.name}", (205, 215, 240)),
            (f"Focus: {sim.active_frame_name}", (180, 200, 235)),
        ]
        for idx, (text_line, line_color) in enumerate(hud_lines):
            text_surf = self._font_hud.render(text_line, True, line_color)
            self._surface.blit(text_surf, (28, 26 + idx * 24))

        legend_text = (
            "SPACE: Reverse | P: Pause | +/-: Speed | R: Reset | TAB: Frame | "
            "1-5: Presets | ESC: Quit"
        )
        legend_surf = self._font_small.render(legend_text, True, (205, 215, 240))
        self._surface.blit(legend_surf, (14, self._surface.get_height() - 24))

    def _draw_scene_overlay(self, *, active_scene: SceneState) -> None:
        """Render Layer 8: modal overlay banner for TITLE and PAUSED scene states."""
        self._overlay_surface.fill((0, 0, 0, 0))
        width = self._surface.get_width()

        if active_scene == SceneState.TITLE:
            banner_x = int((width - 760) * 0.5)
            banner_rect = pygame.Rect(banner_x, 35, 760, 150)
            pygame.draw.rect(
                self._overlay_surface,
                MODAL_BACKDROP_RGBA,
                banner_rect,
                border_radius=8,
            )
            pygame.draw.rect(
                self._overlay_surface,
                MODAL_BORDER_RGBA,
                banner_rect,
                width=1,
                border_radius=8,
            )
            self._surface.blit(self._overlay_surface, (0, 0))

            title_surf = self._font_title.render("Favur - Solar System", True, (255, 230, 140))
            sub_surf = self._font_hud.render(
                "25 J2000 Bodies & 360 Main-Belt Asteroids | Analytical Kepler + Time Reversal",
                True,
                (210, 222, 248),
            )
            prompt_surf = self._font_hud.render(
                "Press ENTER to Start Simulation",
                True,
                DIRECTION_REVERSE_RGB,
            )
            title_x = int((width - title_surf.get_width()) * 0.5)
            sub_x = int((width - sub_surf.get_width()) * 0.5)
            prompt_x = int((width - prompt_surf.get_width()) * 0.5)
            self._surface.blit(title_surf, (title_x, 52))
            self._surface.blit(sub_surf, (sub_x, 98))
            self._surface.blit(prompt_surf, (prompt_x, 134))
        elif active_scene == SceneState.PAUSED:
            banner_x = int((width - 680) * 0.5)
            banner_rect = pygame.Rect(banner_x, 55, 680, 130)
            pygame.draw.rect(
                self._overlay_surface,
                MODAL_BACKDROP_RGBA,
                banner_rect,
                border_radius=8,
            )
            pause_border_rgba = (*DIRECTION_REVERSE_RGB, 230)
            pygame.draw.rect(
                self._overlay_surface,
                pause_border_rgba,
                banner_rect,
                width=1,
                border_radius=8,
            )
            self._surface.blit(self._overlay_surface, (0, 0))

            pause_surf = self._font_title.render("PAUSED", True, DIRECTION_REVERSE_RGB)
            resume_surf = self._font_hud.render(
                "Press P or ENTER to Resume | SPACE to Reverse | +/- Speed | ESC to Quit",
                True,
                (225, 232, 250),
            )
            pause_x = int((width - pause_surf.get_width()) * 0.5)
            resume_x = int((width - resume_surf.get_width()) * 0.5)
            self._surface.blit(pause_surf, (pause_x, 76))
            self._surface.blit(resume_surf, (resume_x, 128))