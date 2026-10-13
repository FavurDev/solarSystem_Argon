"""Pure-Python headless orbital mechanics and solar system simulation package."""

from __future__ import annotations

from solar_system.bodies import (
    KIRKWOOD_GAPS,
    CelestialBody,
    KirkwoodGap,
    VisualStyle,
    build_catalog,
    build_named_bodies,
    generate_asteroid_belt,
)
from solar_system.frames import (
    ReferenceFrame,
    build_frame_registry,
    world_position,
    world_positions,
)
from solar_system.kepler import (
    OrbitalElements,
    keplerian_to_cartesian,
    solve_kepler,
)
from solar_system.simulation import (
    SPEED_LADDER_DAYS_PER_SEC,
    SimulationState,
)
from solar_system.trail import (
    OrbitPoint,
    TrailBuffer,
)
from solar_system.vector import Vec3

__version__ = "0.1.0"

__all__ = [
    "KIRKWOOD_GAPS",
    "SPEED_LADDER_DAYS_PER_SEC",
    "CelestialBody",
    "KirkwoodGap",
    "OrbitPoint",
    "OrbitalElements",
    "ReferenceFrame",
    "SimulationState",
    "TrailBuffer",
    "Vec3",
    "VisualStyle",
    "__version__",
    "build_catalog",
    "build_frame_registry",
    "build_named_bodies",
    "generate_asteroid_belt",
    "keplerian_to_cartesian",
    "solve_kepler",
    "world_position",
    "world_positions",
]
