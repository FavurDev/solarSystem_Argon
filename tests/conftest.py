"""Shared pytest fixtures and AST zero-pygame decoupling audit for the headless model layer."""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

import solar_system
import solar_system.bodies as bodies_mod
import solar_system.frames as frames_mod
import solar_system.kepler as kepler_mod
import solar_system.simulation as simulation_mod
import solar_system.trail as trail_mod
import solar_system.vector as vector_mod
from solar_system import (
    KIRKWOOD_GAPS,
    SPEED_LADDER_DAYS_PER_SEC,
    CelestialBody,
    KirkwoodGap,
    OrbitalElements,
    OrbitPoint,
    ReferenceFrame,
    SimulationState,
    TrailBuffer,
    Vec3,
    VisualStyle,
    build_catalog,
    build_frame_registry,
    build_named_bodies,
    generate_asteroid_belt,
    keplerian_to_cartesian,
    solve_kepler,
    world_position,
    world_positions,
)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

HEADLESS_MODEL_FILES: tuple[str, ...] = (
    "__init__.py",
    "vector.py",
    "kepler.py",
    "frames.py",
    "bodies.py",
    "trail.py",
    "simulation.py",
)


@pytest.fixture
def default_catalog() -> tuple[CelestialBody, ...]:
    """Return the default 25-body + 360-asteroid J2000 catalog (seed=42)."""
    return build_catalog(asteroid_count=360, seed=42)


@pytest.fixture
def bodies_by_name(
    default_catalog: tuple[CelestialBody, ...],
) -> dict[str, CelestialBody]:
    """Return a name-indexed lookup dictionary for the default catalog."""
    return {body.name: body for body in default_catalog}


@pytest.fixture
def frame_registry() -> dict[str, ReferenceFrame]:
    """Return the 8 supported hierarchical reference frames."""
    return build_frame_registry()


@pytest.fixture
def default_simulation() -> SimulationState:
    """Return a fresh SimulationState initialized at J2000.0 in the Sun frame."""
    return SimulationState.create_default(asteroid_count=360, seed=42)


def test_headless_model_modules_contain_zero_pygame_imports() -> None:
    """Verify AST of all headless model modules has zero pygame imports and sys.modules is clean."""
    package_dir = Path(solar_system.__file__).resolve().parent
    offending_imports: list[str] = []

    for filename in HEADLESS_MODEL_FILES:
        file_path = package_dir / filename
        assert file_path.is_file(), f"Missing expected headless model module: {file_path}"
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pygame" or alias.name.startswith("pygame."):
                        offending_imports.append(f"{filename}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                if mod_name == "pygame" or mod_name.startswith("pygame."):
                    offending_imports.append(f"{filename}:{node.lineno} from {mod_name}")

    assert not offending_imports, f"Forbidden pygame imports found: {offending_imports}"

    sim = SimulationState.create_default(asteroid_count=36, seed=42)
    sim.step(1.0)
    assert "pygame" not in sys.modules


def test_public_api_exports_and_default_simulation_fixture(
    default_catalog: tuple[CelestialBody, ...],
    bodies_by_name: dict[str, CelestialBody],
    frame_registry: dict[str, ReferenceFrame],
    default_simulation: SimulationState,
) -> None:
    """Verify all 19 public model exports + __version__ in solar_system.__all__ and fixtures."""
    expected_map: dict[str, object] = {
        "__version__": "0.1.0",
        "Vec3": vector_mod.Vec3,
        "OrbitalElements": kepler_mod.OrbitalElements,
        "solve_kepler": kepler_mod.solve_kepler,
        "keplerian_to_cartesian": kepler_mod.keplerian_to_cartesian,
        "ReferenceFrame": frames_mod.ReferenceFrame,
        "build_frame_registry": frames_mod.build_frame_registry,
        "world_position": frames_mod.world_position,
        "world_positions": frames_mod.world_positions,
        "CelestialBody": bodies_mod.CelestialBody,
        "VisualStyle": bodies_mod.VisualStyle,
        "KirkwoodGap": bodies_mod.KirkwoodGap,
        "KIRKWOOD_GAPS": bodies_mod.KIRKWOOD_GAPS,
        "build_named_bodies": bodies_mod.build_named_bodies,
        "generate_asteroid_belt": bodies_mod.generate_asteroid_belt,
        "build_catalog": bodies_mod.build_catalog,
        "OrbitPoint": trail_mod.OrbitPoint,
        "TrailBuffer": trail_mod.TrailBuffer,
        "SimulationState": simulation_mod.SimulationState,
        "SPEED_LADDER_DAYS_PER_SEC": simulation_mod.SPEED_LADDER_DAYS_PER_SEC,
    }

    assert set(solar_system.__all__) == set(expected_map.keys())
    for name, expected_obj in expected_map.items():
        actual_obj = getattr(solar_system, name)
        assert actual_obj is expected_obj or actual_obj == expected_obj

    assert Vec3 is vector_mod.Vec3
    assert OrbitalElements is kepler_mod.OrbitalElements
    assert solve_kepler is kepler_mod.solve_kepler
    assert keplerian_to_cartesian is kepler_mod.keplerian_to_cartesian
    assert ReferenceFrame is frames_mod.ReferenceFrame
    assert build_frame_registry is frames_mod.build_frame_registry
    assert world_position is frames_mod.world_position
    assert world_positions is frames_mod.world_positions
    assert CelestialBody is bodies_mod.CelestialBody
    assert VisualStyle is bodies_mod.VisualStyle
    assert KirkwoodGap is bodies_mod.KirkwoodGap
    assert KIRKWOOD_GAPS is bodies_mod.KIRKWOOD_GAPS
    assert build_named_bodies is bodies_mod.build_named_bodies
    assert generate_asteroid_belt is bodies_mod.generate_asteroid_belt
    assert build_catalog is bodies_mod.build_catalog
    assert OrbitPoint is trail_mod.OrbitPoint
    assert TrailBuffer is trail_mod.TrailBuffer
    assert SimulationState is simulation_mod.SimulationState
    assert SPEED_LADDER_DAYS_PER_SEC is simulation_mod.SPEED_LADDER_DAYS_PER_SEC

    assert len(default_catalog) == 385
    assert len(bodies_by_name) == 385
    assert "Sun" in bodies_by_name and "Earth" in bodies_by_name
    assert len(frame_registry) == 8
    assert default_simulation.active_frame_name == "Sun"
    positions = default_simulation.step(0.5)
    assert positions["Sun"] == Vec3.ZERO
    assert "pygame" not in sys.modules
