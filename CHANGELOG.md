# Changelog

All notable changes to the `solarSystem` project will be documented in this file.

The format is based on Keep a Changelog (v1.1.0),
and this project adheres to Semantic Versioning (v2.0.0).

## [0.2.0 - Sprint 2] - 2026-10-13

### Added

- **Task 1 — Hybrid Base-10 Logarithmic Display Scaling & Focus-Preserving Orbit Polylines**:
  - Implemented `DisplayScaleConfig`, `heliocentric_distance_to_px` (`[0.30, 375.0] AU` -> `[52.0, 500.0] px`), `moon_distance_to_px` (`[0.00006, 0.04] AU` -> `[16.0, 28.0] px`), `body_display_radius_px`, `world_to_screen`, and 180-vertex true-anomaly `sample_orbit_screen_points` in `src/solar_system/scaling.py`.
  - Added headless unit test suite in `tests/test_scaling.py`.
- **Task 2 — Headless `SceneFSM` State Machine, Normalized Input Vocabulary, and Package Exports**:
  - Implemented `SceneState` (`TITLE`, `SIMULATION`, `PAUSED`, `EXIT`), `InputEvent`, `TitleScene`, `SimulationScene`, `PausedScene`, and `SceneFSM` in `src/solar_system/scenes.py`.
  - Exported all 31 headless model symbols in `src/solar_system/__init__.py` (`__all__`).
  - Added headless unit test suite in `tests/test_scenes.py`.
- **Task 3 — Pygame 2D Scientific Visualization Renderer and HUD Overlay**:
  - Implemented `SolarSystemRenderer` (`1440x1080` deep-space canvas `#060814`, deterministic starfield, 180-vertex Keplerian reference ellipses, Kirkwood asteroid belt layer, fading trajectory trails, Sun/planet/moon/comet discs and labels, telemetry HUD, and `TITLE` / `PAUSED` modal overlays) in `src/solar_system/renderer.py`.
  - Added offscreen Pygame unit test suite in `tests/test_renderer.py`.
- **Task 4 — Pygame 60 FPS Lifecycle, CLI Entry Point, and Visual-Proof Generator**:
  - Implemented `GuiInitializationError`, `init_window`, `translate_pygame_event`, `capture_visual_proof_suite`, `run_app`, `build_arg_parser`, and `main` in `src/solar_system/main.py`.
  - Generated all 7 progressive `1440x1080` visual-proof screenshots (`visual-proof/01_first_light.png` through `visual-proof/07_rate_change.png`) and added offscreen lifecycle/CLI tests in `tests/test_main.py`.
- **Task 5 — Root Documentation (`README.md`)**:
  - Authored root `README.md` documenting runtime prerequisites (`Python 3.11+`), Poetry build/lint/typecheck/test/run commands, architecture summary, hierarchical logarithmic scaling equations (`0.30`, `375.0`, `52.0`, `500.0`, `720`, `540`, `16.0`, `28.0`), keyboard controls, and visual-proof overview.
- **Task 6 — Expanded 8-Module AST Zero-Pygame Audit, Visual-Proof Manifest, and Release Gates**:
  - Expanded `tests/conftest.py` (`HEADLESS_MODEL_MODULES`) to audit all 8 headless model modules (`vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`) for zero `pygame` imports (`SOW-REQ-010`, `TD-001`).
  - Authored `visual-proof/README.md` cataloging all 7 progressive screenshots with milestone steps, simulation epochs (`JD` and ISO UTC), directions, warp rates, keyboard input sequences, and observable visual features (`SOW-REQ-009`).
  - Added `tests/test_visual_proof.py` verifying all 7 PNG headers, `1440x1080` `IHDR` dimensions, non-uniform pixel content, `visual-proof/README.md`, and root `README.md` (`SOW-REQ-009`, `SOW-REQ-015`).

## [0.1.0 - Sprint 1] - 2026-10-13

### Added

- **Task 1 — Poetry Project Configuration, `.gitignore` Hygiene, and Headless Package Root**:
  - Initialized Python 3.13 Poetry workspace (`pyproject.toml`, `poetry.lock`) with `pygame >= 2.6.0`, `pytest`, `pytest-cov`, `ruff`, and `mypy --strict`.
  - Configured `.gitignore` exclusions for `.favur/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, and `dist/`.
  - Created headless package root (`src/solar_system/__init__.py` with `__version__ = "0.1.0"`) and test package marker (`tests/__init__.py`) with zero `pygame` imports.
- **Task 2 — Immutable 3D Vector Algebra and Safeguarded Newton-Raphson Keplerian Solver**:
  - Implemented `@dataclass(frozen=True, slots=True) class Vec3` in `src/solar_system/vector.py` supporting 3D Euclidean arithmetic, dot/cross products, safe zero-vector normalization, and active Euler X/Z axis rotations (`rotate_x`, `rotate_z`).
  - Implemented `OrbitalElements`, `solve_kepler`, `true_anomaly_from_eccentric`, `keplerian_to_cartesian`, and `orbital_period_days` in `src/solar_system/kepler.py` with safeguarded Newton-Raphson iteration (`|E - e*sin(E) - M| < 1e-12`) across circular, moderate, and high-eccentricity (`e <= 0.995086`) regimes and 3-1-3 Euler perifocal-to-ecliptic coordinate rotations.
  - Added unit test suite in `tests/test_vector.py` and `tests/test_kepler.py`.
- **Task 3 — Bounded `TrailBuffer` FIFO Ring Buffer with Reference-Frame Eviction**:
  - Implemented immutable `OrbitPoint` (`x_au`, `y_au`, `jd`) and `collections.deque`-backed `TrailBuffer` (`max_points = 480`) in `src/solar_system/trail.py` with FIFO eviction and automatic trail history clearing when switching reference frames.
  - Added unit test suite in `tests/test_trails.py`.
- **Task 4 — Hierarchical `ReferenceFrame` Registry and Parent-Chain Transformations**:
  - Implemented `ReferenceFrame`, `BodyLookup` protocol, `build_frame_registry()` (8 frames: `Sun`, `Earth`, `Moon`, `Mars`, `Jupiter`, `Saturn`, `Uranus`, `Neptune`), recursive `heliocentric_position` with cycle/missing-parent guards, `world_position`, `world_positions`, and `body_trajectory_in_frame` in `src/solar_system/frames.py`.
  - Added unit test suite in `tests/test_frames.py` verifying origin invariance, antisymmetry, lunar/Jovian hierarchical offsets, and Mars geocentric apparent retrograde motion.
- **Task 5 — 25-Body J2000 Solar System Catalog and Deterministic Kirkwood-Gap Asteroid Belt**:
  - Implemented `CelestialBody`, `VisualStyle`, `KirkwoodGap`, `KIRKWOOD_GAPS` (4:1, 3:1, 5:2, 7:3, and 2:1 Jupiter mean-motion resonances), and `build_named_bodies()` in `src/solar_system/bodies.py` covering the Sun, 8 planets, 9 moons (including retrograde Triton at `i = 156.865 deg`), 4 minor/dwarf bodies (`Ceres`, `Vesta`, `Pallas`, `Pluto`), and 3 comets (`1P/Halley`, `2P/Encke`, `Hale-Bopp`).
  - Implemented `generate_asteroid_belt(count=360, seed=42)` and `build_catalog()` using isolated `random.Random(seed)` rejection sampling outside all 5 Kirkwood resonance gap intervals.
  - Added unit test suites in `tests/test_bodies.py` and `tests/test_kirkwood.py`.
- **Task 6 — Headless `SimulationState` Clock, Speed Ladder, Time-Reversal, and Scene Controls**:
  - Implemented `SimulationState`, `SPEED_LADDER_DAYS_PER_SEC`, and `jd_to_iso_date` in `src/solar_system/simulation.py` supporting deterministic time stepping, exact bidirectional time reversal (`reverse_direction()`), discrete speed ladder clamping (`speed_up()`, `slow_down()`), pause/resume, epoch reset (`J2000_EPOCH_JD`), reference-frame switching with trail clearing, scene preset selection, body focus, zoom, and pan controls.
  - Added unit test suites in `tests/test_time_reversal.py` and `tests/test_controls.py`.
- **Task 7 — Shared Pytest Fixtures, AST Zero-Pygame Decoupling Audit, and 90% Model Coverage Gate**:
  - Implemented shared pytest fixtures (`default_catalog`, `bodies_by_name`, `frame_registry`, `default_simulation`) and AST zero-`pygame` decoupling audit tests in `tests/conftest.py`.
  - Exported the full 19-symbol headless model API in `src/solar_system/__init__.py` (`__all__`).
  - Verified all 68 headless unit tests across all 7 required SOW sub-suites plus `test_vector.py` and `conftest.py` pass with `98.47%` model line coverage (satisfying `[QAC-1.1]` `>= 90%` threshold) and zero `ruff` or `mypy --strict` diagnostics.
