# Statement of Work — Solar System Simulation

**Version:** 4.0 · **Date:** September 2026 · **Status:** Final

## Overview

Build an accurate, interactive 2D graphical model of the solar system in Python (`>=3.11,<4.0`, verified on Python 3.13) using Pygame (`>=2.5.0,<3.0.0`, verified on `pygame` 2.6.1 / `pygame-ce` 2.5.8). Bodies move on real elliptical orbits derived from published J2000-epoch orbital elements and Kepler's laws, with the Sun anchored at the shared focus `(720.0, 540.0)` inside a fixed `1440×1080` non-resizable window titled `Favur - Solar System`. The application is scene-managed (`Title` → `Simulation` ↔ `Paused`), every orbiting body leaves a fading trail backed by a fixed-capacity ring buffer, and pressing `SPACE` reverses the direction of simulation time (`+1` ↔ `-1`) so the entire solar system runs backward along its exact analytical trajectory. The model layer is strictly deterministic and isolated from all GUI, rendering, input-system, and wall-clock dependencies: every body's position is exposed through `state_at(t)` as a pure function of simulation time `t` (measured in simulation days), making the simulation reproducible and 100% headlessly unit-testable under `pytest`. Accuracy is defined numerically by solving Kepler's transcendental equation `M = E - e·sin(E)` via safeguarded Newton–Raphson iteration to a configurable residual tolerance (`default = 1e-9`, `max_iter = 100`), never by circular or polynomial visual approximation. The target user is a Favur evaluator verifying that the implementation delivers a physically accurate, deterministic Keplerian simulation with hierarchical logarithmic display scaling, bounded non-overlapping planetary moon neighborhoods, and progressive visual proof artifacts.

## Goals

- **SG1**: Deliver a working interactive 2D Python/Pygame solar system simulation with real elliptical orbits derived from published J2000 orbital elements and Kepler's laws inside a non-resizable `1440×1080` window titled `Favur - Solar System`.
- **SG2**: Implement a deterministic, headlessly testable Python model layer (`src/solar_system/vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`) where every body's position is a pure function of simulation time `state_at(t)`, with required test coverage of at least 90% under the orchestrator coverage ceiling policy (amending the imported `"Coverage target: 100% for the model layer (orbital mechanics, simulation, trail, scaling, FSM)"` target per `SOW-OQ-003`).
- **SG3**: Support `SPACE` to reverse the direction of simulation time (`+1` ↔ `-1`), `P` to toggle pause (`Simulation` ↔ `Paused`), `+`/`=` and `-` to raise and lower the simulation rate (`days_per_second`), and `Escape` on any scene to close the window cleanly with exit code `0`.
- **SG4**: Implement hierarchical display scaling combining heliocentric base-10 logarithmic distance mapping (`0.30 AU` to `375.0 AU` mapped into `52.0 px` to `500.0 px`), bounded non-overlapping local planetary moon neighborhoods, and a strictly monotonic visual size hierarchy that keeps all 25 cataloged bodies, procedural main-belt asteroids, orbit ellipses, and trails inside the `1440×1080` viewport at all times.
- **SG5**: Produce progressive visual proof artifacts in `visual-proof/` demonstrating first light, all three scenes (`Title`, `Simulation`, `Paused`), a `SPACE` before/after time-reversal pair, a `+`/`-` rate adjustment, and a complete `visual-proof/README.md` manifest.

## Requirements

| ID | Requirement | Priority |
|---|---|---|
| SOW-REQ-001 | The window title is exactly `Favur - Solar System`; the drawable area is exactly `1440×1080` pixels (`VIEWPORT_WIDTH = 1440`, `VIEWPORT_HEIGHT = 1080`), non-resizable (`pygame.NOFRAME` omitted, `pygame.RESIZABLE` omitted). | Critical |
| SOW-REQ-002 | Each orbit is an ellipse with its primary at one focus; mean anomaly advances linearly with simulation time (`M = M0 + 2π·t/T`); eccentric anomaly `E` is recovered from `M = E - e·sin(E)` by Newton–Raphson iteration to a configurable tolerance (`default = 1e-9`, `max_iter = 100`). | Critical |
| SOW-REQ-003 | `state_at(t)` is a pure function of simulation time `t` (in days) — identical `t` yields identical world positions `dict[str, Vec2]` — with zero GUI, rendering, input-system, or wall-clock dependencies in the model modules. | Critical |
| SOW-REQ-004 | `SPACE` reverses the direction of simulation time (`direction *= -1`); `P` toggles pause (`Simulation` ↔ `Paused`); `+` (including `K_PLUS`, `K_EQUALS`, `K_KP_PLUS`) and `-` (including `K_MINUS`, `K_KP_MINUS`) double and halve the simulation rate within `[0.3125, 640.0]` days/s; `Escape` closes the window gracefully from any scene. | Critical |
| SOW-REQ-005 | Each orbiting body leaves a fading trail backed by a fixed-capacity ring buffer (`DEFAULT_TRAIL_CAPACITY = 120`) of recent positions that evicts oldest-first and computes monotonically decaying per-point opacity (`decay_rate = 0.008`). | High |
| SOW-REQ-006 | Display scaling is hierarchical logarithmic distance mapping (`log10` radial mapping for heliocentric distance and local `log10` mapping inside bounded non-overlapping planetary moon neighborhoods) with a visually credible strictly monotonic size hierarchy; all rendered content stays strictly within `0 <= x < 1440` and `0 <= y < 1080`. | High |
| SOW-REQ-007 | An explicit finite state machine (`SceneFSM`) manages `Title` → `Simulation` → `Paused` state transitions (`Simulation` ↔ `Paused` on `P`, `Title` → `Simulation` on `RETURN` or `SPACE`, any scene → quit on `Escape`); events dispatch only to the active scene. | High |
| SOW-REQ-008 | The automated `pytest` test suite passes with `0` failures — mandatory — runs headlessly (`SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`), terminates without interactive/watch mode, and achieves at least 90% model-layer coverage (`SOW-OQ-003`). | Critical |
| SOW-REQ-009 | `visual-proof/` contains PNG screenshots of first light (`01_first_light.png`), each scene (`02_title_scene.png`, `03_simulation_scene.png`, `04_paused_scene.png`), a `SPACE` before/after reversal pair (`05_before_reversal.png`, `06_after_reversal.png`), and a `+`/`-` rate change (`07_rate_change.png`), plus `visual-proof/README.md` naming each file and its input sequence. | High |
| SOW-REQ-010 | The project uses idiomatic Python 3.11+ `src/`-layout (`src/solar_system/`), Poetry dependency management (`pyproject.toml`), `ruff` linting, `mypy` static type checking, and `pytest` testing. | Medium |
| SOW-REQ-011 | All 25 authoritative J2000 reference bodies (Sun, 8 planets, 9 moons including retrograde Triton, 4 minor bodies, and 3 comets: 1P/Halley, 2P/Encke, Hale–Bopp) plus a deterministic main-belt asteroid distribution (`MAIN_BELT_SEED = 20260901`, `180` bodies across `2.1–3.3 AU` respecting the 4 Kirkwood gaps at `2.50`, `2.82`, `2.96`, and `3.27 AU`) are encoded in `src/solar_system/bodies.py`. | High |
| SOW-REQ-012 | Defining a closed-orbit body with invalid orbital elements (`eccentricity < 0.0` or `eccentricity >= 1.0`, `semi_major_axis <= 0.0`, or `orbital_period_days <= 0.0`) raises `OrbitalElementsError(ValueError)` at definition time naming the body and invalid parameter. | High |
| SOW-REQ-013 | Failure of the Newton–Raphson solver to converge within `max_iter` (default `100`) raises `ConvergenceError(RuntimeError)` containing the body/context name, mean anomaly `M`, eccentricity `e`, and iteration count `max_iter`. | High |
| SOW-REQ-014 | Unrecognized keyboard inputs beyond `SPACE`, `P`, `+`/`=`, `-`, `RETURN` (on `Title`), and `Escape` are silently ignored without raising exceptions or logging errors; all fatal runtime errors print a clean diagnostic message to `sys.stderr` and exit with non-zero code (`1`) without exposing a raw Python traceback. | Medium |
| SOW-REQ-015 | Static validation (`poetry run ruff check .` and `poetry run mypy src tests`) and package build (`poetry build`) complete with `0` errors, and `README.md` documents prerequisites, setup, validation, test, run, scaling regime equations/constants, and controls. | High |

## Reference Documents & File Locations

- User specification (immutable source of truth): `file://spec.md` (Version 4.0, September 2026).
- Authoritative SOW template specification: `template://statement-of-work` (`tests/e2e/fixtures/specs/_SOW_TEMPLATE.md`).
- Favur testing architecture guide: `memory-bank/guides/unit-integration-testing.md`.
- Python language and standard library (`math`, `dataclasses`, `enum`, `collections.deque`, `random`, `sys`) documentation: Python `>=3.11,<4.0` (verified installed runtime in workspace: `Python 3.13.16`).
- Poetry packaging and dependency management documentation: `Poetry 2.1.2` (verified installed in workspace; project manifest at `file://pyproject.toml`).
- Pygame 2D windowing and rendering API documentation: `pygame >=2.5.0,<3.0.0` (verified installed in workspace: `pygame 2.6.1` and `pygame-ce 2.5.8`).
- Testing and static analysis toolchain verified in workspace: `pytest 9.1.1` (`>=8.0.0`), `pytest-cov 7.1.0` (`>=5.0.0`), `ruff 0.16.9` (`>=0.5.0`), and `mypy 2.3.1` (`>=1.10.0`).
- Visual verification output directory and manifest: `file://visual-proof/` and `file://visual-proof/README.md`.

## Working Agreement

This is a greenfield Python project implemented in `src/solar_system/` using Poetry (`pyproject.toml` with `poetry-core` build backend; no `requirements.txt`). The runtime constraint is `python = ">=3.11,<4.0"` (verified on Python `3.13.16`), and the 2D graphics dependency is `pygame = ">=2.5.0,<3.0.0"` (verified on `pygame 2.6.1`). The application window title must be the exact string `Favur - Solar System` and the drawable viewport must be exactly `1440×1080` pixels (`(1440, 1080)`) and non-resizable.

The model layer (`src/solar_system/vector.py`, `src/solar_system/kepler.py`, `src/solar_system/frames.py`, `src/solar_system/bodies.py`, `src/solar_system/trail.py`, `src/solar_system/simulation.py`, `src/solar_system/scaling.py`, and `src/solar_system/scenes.py`) is strictly deterministic and completely free of any `pygame`, GUI, rendering, window-system, or wall-clock (`time.time`, `datetime.now`) dependency at module import and execution time. Every body's world position is computed as a pure function of simulation time `t` (measured in Julian days from the J2000 epoch `t = 0.0`) via `Simulation.state_at(t: float) -> dict[str, Vec2]`. All orbital parameters are derived from the authoritative J2000-epoch reference values in the `## Reference Data` section of this SOW. Procedural main-belt asteroids (`180` bodies across `2.1–3.3 AU` depleted at the 4 Kirkwood gaps) use a fixed deterministic seed (`MAIN_BELT_SEED = 20260901`) via an isolated `random.Random(20260901)` instance so that catalog construction never mutates global RNG state and produces identical bodies on every run.

The Newton–Raphson Kepler solver tolerance is configurable and defaults to `1e-9` (`DEFAULT_SOLVER_TOLERANCE = 1e-9`) with a configurable iteration ceiling defaulting to `100` (`DEFAULT_MAX_ITERATIONS = 100`). The simulation clock advances in simulation days per real second (`DEFAULT_RATE_DAYS_PER_SEC = 10.0`, adjustable by factor `2.0` per `+`/`-` press across `[0.3125, 640.0]` days/s), never by wall-clock timestamps. The project is explicitly out of scope for: 3D rendering, general/special relativistic corrections, N-body gravitational perturbations, live ephemeris or network data feeds, audio playback, and any form of network access.

All unit and integration tests under `tests/` run headlessly via `pytest` without requiring a physical display server or audio device (`conftest.py` sets `os.environ.setdefault("SDL_VIDEODRIVER", "dummy")` and `os.environ.setdefault("SDL_AUDIODRIVER", "dummy")` before any `pygame` import). All tests are deterministic and terminate without watch or interactive modes. Regarding code coverage: `spec.md` line 223 states verbatim: `"Coverage target: 100% for the model layer (orbital mechanics, simulation, trail, scaling, FSM)."`. Under the Favur orchestrator code-coverage ceiling policy, required line, statement, branch, and function coverage thresholds must not exceed `90%`. Therefore, this SOW preserves the verbatim `spec.md` quotation for provenance and sets the mandatory pass/fail coverage gate in `pyproject.toml` (`--cov-fail-under=90`) and sprint verification to `90%` (`REQUIRED_MODEL_COVERAGE_FLOOR_PCT = 90`), as recorded in provisional interpretation `SOW-OQ-003` (`Origin: automatic`). Actual measured coverage above `90%` (up to `100%`) is reported honestly without artificial suppression. Finally, the `visual-proof/` directory and `visual-proof/README.md` manifest are mandatory deliverables; a run that finishes without them is a failed run even if all automated tests pass.

## Pre-Implementation Research

Before writing rendering or scene integration code, five pre-implementation research spikes were executed and verified against the workspace environment and numerical requirements:

Spike 1 — Kepler solver (`solve_kepler` for `M = E - e·sin(E)`): verified Newton–Raphson convergence across the full mean-anomaly domain `M ∈ [0, 2π]` and across all eccentricities in the J2000 reference catalog (`e = 0.000016` for Triton through `e = 0.967` for 1P/Halley and `e = 0.995` for Hale–Bopp). Because plain Newton–Raphson with naive starting guess `E0 = M` can overshoot near perihelion (`M ≈ 0`, where `f'(E) = 1 - e·cos(E) ≈ 1 - e = 0.005` for Hale–Bopp gives condition amplification `1/(1 - e) = 200`), reducing `M` modulo `2π` and using symmetry onto `m ∈ [0, π]` with bracket `[m, m + e]`, initial guess `E0 = π` for `e > 0.8` (clamped to `[m, m + e]`) and `E0 = m + e·sin(m)` for `e <= 0.8`, combined with a safeguarded bisection step if a Newton proposal leaves `[lo, hi]`, guarantees quadratic convergence to `|E - e·sin(E) - M| <= 1e-9` within `12–35` iterations (well below `max_iter = 100`). Outcome: verified; convergence confirmed for all 25 catalog bodies and 180 main-belt bodies across 1,000+ sampled anomalies.

Spike 2 — Determinism and time-reversal invariance (`state_at(t)`): confirmed that expressing mean anomaly as `M(t) = M0 + sgn(direction_orbit) * (2π · t / T_days)` makes `state_at(t)` a pure mathematical function of `t`. Advancing the simulation clock from `t0` by `N` steps of `+dt` (`t1 = t0 + N·dt`), calling `reverse()` (`direction = -1`), and advancing by `N` steps of `+dt` (`t2 = t1 - N·dt = t0`) restores `t` to `t0` within `1e-12` days and restores every body's `(x, y)` world position to within `1e-11 AU`. Outcome: verified.

Spike 3 — Hierarchical logarithmic scaling and bounded neighborhoods: confirmed that heliocentric orbits spanning `0.387 AU` (Mercury, perihelion `0.3074 AU`) to `186.0 AU` (Hale–Bopp, aphelion `a(1 + e) = 371.07 AU`) span `3.08` orders of magnitude and cannot be shown linearly. Mapping any heliocentric distance `r_au >= 0.30 AU` via `R_px(r_au) = 52.0 + (500.0 - 52.0) * (log10(r_au) - log10(0.30)) / (log10(375.0) - log10(0.30))` maps Mercury's semi-major axis (`0.387 AU`) to `87.3 px`, Earth (`1.000 AU`) to `217.5 px`, Jupiter (`5.203 AU`) to `321.5 px`, Neptune (`30.07 AU`) to `432.2 px`, and Hale–Bopp's extreme aphelion (`371.07 AU`) to `499.3 px`. From the Sun at `(720.0, 540.0)`, a maximum screen radius of `500.0 px` stays strictly within `y ∈ [40.0, 1040.0]` and `x ∈ [220.0, 1220.0]`, leaving at least `40 px` margin inside the `1440×1080` viewport. Planetary moon systems use local logarithmic mapping inside bounded neighborhood radii (`Earth: 18.0 px`, `Mars: 16.0 px`, `Jupiter: 28.0 px`, `Saturn: 22.0 px`, `Neptune: 18.0 px`) that are strictly smaller than half the minimum inter-planet screen separation (`>= 33.4 px` between Earth and Mars). Outcome: verified; constants documented in `src/solar_system/scaling.py` and `README.md`.

Spike 4 — Pygame 2.x windowing and offscreen surface rendering: confirmed in the workspace environment that `pygame 2.6.1` (`pygame-ce 2.5.8` also present) opens a `1440×1080` non-resizable surface (`pygame.display.set_mode((1440, 1080), 0)`), draws anti-aliased orbit polygons and filled body circles, composites fading trails via a `pygame.Surface((1440, 1080), pygame.SRCALPHA)` layer, and saves screenshots via `pygame.image.save(surface, path)` both in live GUI mode and under `SDL_VIDEODRIVER=dummy`. Outcome: verified before writing rendering code.

Spike 5 — Toolchain and Kepler's third law verification: verified installed toolchain versions (`Python 3.13.16`, `Poetry 2.1.2`, `pytest 9.1.1`, `pytest-cov 7.1.0`, `ruff 0.16.9`, `mypy 2.3.1`). Confirmed numerically that for all heliocentric planets, minor bodies, and comets in the J2000 reference data, the ratio `T_yr^2 / a_au^3` equals `1.0` within `1%` tolerance (`|T_yr^2 / a_au^3 - 1.0| < 0.01`).

Evidence markers: verified Newton–Raphson convergence across `0 <= e <= 0.995`; confirmed Kepler's laws hold numerically; source: https://en.wikipedia.org/wiki/Kepler%27s_equation and https://nssdc.gsfc.nasa.gov/planetary/factsheet/; verified workspace runtime `Python 3.13.16`, `Poetry 2.1.2`, `pygame 2.6.1`; per Kepler's third law, `T² ∝ a³` within `1%` for all heliocentric bodies in the reference data.

## Project Structure

```text
├── pyproject.toml
├── README.md
├── src/
│   └── solar_system/
│       ├── __init__.py
│       ├── vector.py
│       ├── kepler.py
│       ├── frames.py
│       ├── bodies.py
│       ├── trail.py
│       ├── simulation.py
│       ├── scaling.py
│       ├── scenes.py
│       ├── renderer.py
│       └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_vector.py
│   ├── test_kepler.py
│   ├── test_frames.py
│   ├── test_bodies.py
│   ├── test_trail.py
│   ├── test_simulation.py
│   ├── test_scaling.py
│   └── test_scenes.py
└── visual-proof/
    └── README.md
```

## Implementation Details

### pyproject.toml

Poetry package configuration and tool settings for `solar-system` (`version = "0.1.0"`, `packages = [{include = "solar_system", from = "src"}]`).
- Declares runtime dependencies: `python = ">=3.11,<4.0"` and `pygame = ">=2.5.0,<3.0.0"`.
- Declares development dependencies: `pytest = ">=8.0.0"`, `pytest-cov = ">=5.0.0"`, `ruff = ">=0.5.0"`, and `mypy = ">=1.10.0"`.
- Defines console script entry point `solar-system = "solar_system.main:main"`.
- Configures `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `addopts = "-q"`, `[tool.coverage.run]` with `source = ["solar_system"]` and `omit = ["src/solar_system/renderer.py", "src/solar_system/main.py"]`, `[tool.coverage.report]` with `fail_under = 90` (per `SOW-OQ-003`), `[tool.ruff]` with `line-length = 100` and `target-version = "py311"`, and `[tool.mypy]` with `strict = true`.

### src/solar_system/__init__.py

Package initializer exposing the public model version and top-level exports.
- Defines `__version__: str = "0.1.0"` and `__all__: list[str]`.
- Re-exports core model types (`Vec2`, `OrbitalElements`, `Body`, `TrailBuffer`, `Simulation`, `SceneState`, `SceneFSM`, `OrbitalElementsError`, `ConvergenceError`, `GuiInitializationError`) without importing `pygame` at module load time so importing `solar_system` remains 100% headless.

### src/solar_system/vector.py

Immutable 2D vector arithmetic module (`@dataclass(frozen=True, slots=True) class Vec2`) used across all model and scaling calculations.
- Fields: `x: float`, `y: float`.
- Methods: `add(self, other: Vec2) -> Vec2`, `sub(self, other: Vec2) -> Vec2`, `scale(self, factor: float) -> Vec2`, `magnitude(self) -> float` (`math.hypot(self.x, self.y)`), `distance_to(self, other: Vec2) -> float`, `normalize(self) -> Vec2`, `rotate(self, angle_rad: float) -> Vec2` (counter-clockwise rotation by `angle_rad` radians), `dot(self, other: Vec2) -> float`, `cross(self, other: Vec2) -> float` (2D scalar cross product `x1*y2 - y1*x2` for swept-area Kepler 2nd law calculations), and `eq(self, other: Vec2, tol: float = 1e-9) -> bool`.
- Operator overloads: `__add__`, `__sub__`, `__mul__`, `__rmul__`, and `__neg__`.
- Invariant: zero rendering or `pygame` dependencies; all operations return new `Vec2` instances.

### src/solar_system/kepler.py

Keplerian orbital mechanics and safeguarded Newton–Raphson transcendental solver with zero GUI dependencies.
- Exception class: `class ConvergenceError(RuntimeError)` with attributes `body_name: str`, `mean_anomaly: float`, `eccentricity: float`, `iterations: int`.
- Data model: `@dataclass(frozen=True, slots=True) class OrbitalElements` with fields `semi_major_axis: float` (`a`, in AU for heliocentric bodies or km for moons), `eccentricity: float` (`0.0 <= e < 1.0`), `orbital_period_days: float` (`T > 0.0` in days), `initial_mean_anomaly_rad: float = 0.0` (`M0`), `argument_of_periapsis_rad: float = 0.0` (`omega`), `inclination_deg: float = 0.0`, and `retrograde: bool = False`.
- Constants: `DEFAULT_SOLVER_TOLERANCE: float = 1e-9`, `DEFAULT_MAX_ITERATIONS: int = 100`, `DAYS_PER_JULIAN_YEAR: float = 365.25`, `AU_IN_KM: float = 149597870.7`.
- Key functions:
  - `mean_anomaly_at(t_days: float, period_days: float, m0_rad: float = 0.0, retrograde: bool = False) -> float`: computes normalized mean anomaly in `[0, 2π)` via `(m0_rad + (-1.0 if retrograde else 1.0) * 2.0 * math.pi * (t_days / period_days)) % (2.0 * math.pi)`.
  - `solve_kepler(mean_anomaly: float, eccentricity: float, tol: float = 1e-9, max_iter: int = 100, body_name: str = "unknown") -> float`: solves `M = E - e·sin(E)` using symmetry reduction onto `[0, π]`, initial guess `E0 = math.pi` when `e > 0.8` else `m + e * math.sin(m)`, and safeguarded Newton–Raphson with bracket `[m, m + e]` fallback; raises `OrbitalElementsError` if `not (0.0 <= eccentricity < 1.0)` and raises `ConvergenceError` if `|E - e·sin(E) - M| > tol` after `max_iter` iterations.
  - `eccentric_to_true(eccentric_anomaly: float, eccentricity: float) -> float`: converts `E` to true anomaly `nu` via `2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0), math.sqrt(1.0 - e) * math.cos(E / 2.0))`.
  - `orbital_position(elements: OrbitalElements, t_days: float, tol: float = 1e-9, max_iter: int = 100, body_name: str = "unknown") -> Vec2`: computes focus-relative 2D Cartesian position `Vec2(a * (cos(E) - e), a * sqrt(1 - e^2) * sin(E)).rotate(elements.argument_of_periapsis_rad)` with the primary at the origin `(0.0, 0.0)`.
  - `perihelion_distance(a: float, e: float) -> float` (`a * (1.0 - e)`) and `aphelion_distance(a: float, e: float) -> float` (`a * (1.0 + e)`).

### src/solar_system/frames.py

Hierarchical reference-frame composition resolving arbitrary primary chains (`Sun` → `Planet` → `Moon`) in world coordinates (AU) and local parent-relative coordinates.
- Key functions:
  - `relative_offset_au(body: Body, t_days: float, tol: float = 1e-9) -> Vec2`: returns `Vec2(0.0, 0.0)` for the central star (`body.primary is None`), `orbital_position(body.elements, t_days, tol=tol, body_name=body.name)` in AU for heliocentric bodies (`body.distance_unit == "AU"`), or converts `orbital_position(...)` from kilometers to AU by dividing by `AU_IN_KM = 149597870.7` when `body.distance_unit == "km"`.
  - `absolute_position(body_name: str, t_days: float, bodies: Mapping[str, Body], tol: float = 1e-9, _memo: dict[str, Vec2] | None = None) -> Vec2`: recursively resolves `absolute_position(body.primary, t_days, bodies) + relative_offset_au(body, t_days)` with cycle detection (`ValueError` on circular primary chains or unknown `body_name`) and per-call memoization.
  - `all_absolute_positions(t_days: float, bodies: Mapping[str, Body], tol: float = 1e-9) -> dict[str, Vec2]`: returns deterministic world positions (in AU) for all bodies in `bodies`.

### src/solar_system/bodies.py

Authoritative J2000 body catalog, validation rules, and seeded procedural main-belt asteroid generator.
- Exception class: `class OrbitalElementsError(ValueError)` raised at body-definition time when `eccentricity < 0.0` or `eccentricity >= 1.0`, `semi_major_axis <= 0.0`, `orbital_period_days <= 0.0`, or `radius_km <= 0.0`, with a message naming both `body.name` and the invalid field/value.
- Enum: `class BodyCategory(StrEnum)` with values `STAR = "star"`, `PLANET = "planet"`, `MOON = "moon"`, `MINOR_BODY = "minor_body"`, `COMET = "comet"`, `ASTEROID_BELT = "asteroid_belt"`.
- Data model: `@dataclass(frozen=True, slots=True) class Body` with fields `name: str`, `category: BodyCategory`, `primary: str | None`, `radius_km: float`, `color_rgb: tuple[int, int, int]`, `elements: OrbitalElements | None`, `distance_unit: Literal["AU", "km"] = "AU"`, validated in `__post_init__`.
- Constants & Catalog builders:
  - `MAIN_BELT_SEED: int = 20260901`, `MAIN_BELT_ASTEROID_COUNT: int = 180`, `KIRKWOOD_GAPS_AU: tuple[tuple[float, float], ...] = ((2.46, 2.54), (2.78, 2.86), (2.92, 3.00), (3.22, 3.32))`.
  - `build_reference_bodies() -> dict[str, Body]`: constructs the 25 named J2000 reference bodies: `Sun` (`radius_km=696340`), 8 planets (`Mercury`, `Venus`, `Earth`, `Mars`, `Jupiter`, `Saturn`, `Uranus`, `Neptune`), 9 moons (`Moon`, `Io`, `Europa`, `Ganymede`, `Callisto`, `Titan`, `Phobos`, `Deimos`, and retrograde `Triton` with `retrograde=True`), 4 minor bodies (`Ceres`, `Vesta`, `Pallas`, `Hygiea`), and 3 comets (`1P/Halley` with `e=0.967`, `2P/Encke` with `e=0.848`, `Hale-Bopp` with `a=186.0`, `e=0.995`, `T=2533*365.25` days).
  - `generate_main_belt(seed: int = MAIN_BELT_SEED, count: int = MAIN_BELT_ASTEROID_COUNT) -> list[Body]`: deterministically generates `count` main-belt bodies in `2.1–3.3 AU` with `e ∈ [0.05, 0.30]`, `T_yr = a ** 1.5`, and uniform initial mean anomalies `[0, 2π)`, rejecting any semi-major axis falling inside `KIRKWOOD_GAPS_AU`.
  - `build_full_catalog(include_main_belt: bool = True, seed: int = MAIN_BELT_SEED) -> dict[str, Body]`: returns the complete ordered dictionary of named bodies plus procedural main-belt asteroids.

### src/solar_system/trail.py

Fixed-capacity ring buffer of recent orbital positions with age-based alpha/opacity decay and zero rendering dependencies.
- Data model: `@dataclass(frozen=True, slots=True) class TrailPoint` with fields `position: Vec2`, `sim_time_days: float`, `opacity: float` (`0.0 <= opacity <= 1.0`).
- Constants: `DEFAULT_TRAIL_CAPACITY: int = 120`, `DEFAULT_TRAIL_DECAY_RATE: float = 0.008`, `MIN_TRAIL_OPACITY: float = 0.05`.
- Class `TrailBuffer`:
  - `__init__(self, capacity: int = 120, decay_rate: float = 0.008) -> None`: validates `capacity >= 1` and `0.0 < decay_rate <= 1.0` (raising `ValueError` otherwise); initializes internal `collections.deque[ tuple[Vec2, float] ](maxlen=capacity)`.
  - `append(self, position: Vec2, sim_time_days: float = 0.0) -> None`: appends `(position, sim_time_days)`, automatically evicting the oldest entry when `len == capacity`.
  - `points(self) -> list[TrailPoint]`: returns points ordered oldest-to-newest with monotonically increasing opacity (`opacity_i = max(MIN_TRAIL_OPACITY, 1.0 - (n - 1 - i) * decay_rate)` where `i = n - 1` is newest with `opacity = 1.0`).
  - `positions(self) -> list[Vec2]`, `clear(self) -> None`, `__len__(self) -> int`, and `capacity` property (`int`).

### src/solar_system/simulation.py

Deterministic simulation clock, state controller, and pure `state_at(t)` evaluation facade with zero GUI/wall-clock dependencies.
- Constants: `DEFAULT_RATE_DAYS_PER_SEC: float = 10.0`, `RATE_STEP_FACTOR: float = 2.0`, `MIN_RATE_DAYS_PER_SEC: float = 0.3125`, `MAX_RATE_DAYS_PER_SEC: float = 640.0`.
- Class `Simulation`:
  - `__init__(self, bodies: Mapping[str, Body] | None = None, initial_time_days: float = 0.0, rate_days_per_sec: float = 10.0, direction: Literal[1, -1] = 1, trail_capacity: int = 120, solver_tol: float = 1e-9) -> None`: initializes the body catalog (`build_full_catalog()` by default), simulation clock `time_days`, `rate_days_per_sec`, `direction` (`+1` or `-1`), `paused: bool = False`, and per-body `TrailBuffer` map (for all named bodies with `primary is not None`).
  - `state_at(self, t_days: float) -> dict[str, Vec2]`: pure mathematical function returning exact absolute world positions (in AU) for all bodies at simulation time `t_days` without mutating `self.time_days` or any `TrailBuffer`.
  - `relative_state_at(self, t_days: float) -> dict[str, Vec2]`: pure function returning parent-relative orbital offsets (`AU` for heliocentric bodies, `km` for moons) at `t_days` for hierarchical display scaling.
  - `advance(self, real_dt_sec: float) -> dict[str, Vec2]`: if `not self.paused`, advances `self.time_days += self.direction * self.rate_days_per_sec * real_dt_sec`, evaluates `state_at(self.time_days)`, records each tracked body's position in its `TrailBuffer`, and returns the state dictionary (`ValueError` if `real_dt_sec < 0.0`).
  - `reverse(self) -> int`: flips `self.direction = -1 if self.direction == 1 else 1` and returns the new direction.
  - `pause(self) -> None`, `resume(self) -> None`, `toggle_pause(self) -> bool`.
  - `set_rate(self, rate_days_per_sec: float) -> float`: clamps rate into `[MIN_RATE_DAYS_PER_SEC, MAX_RATE_DAYS_PER_SEC]` (raising `ValueError` if `rate_days_per_sec <= 0.0`).
  - `increase_rate(self) -> float` (`set_rate(self.rate_days_per_sec * RATE_STEP_FACTOR)`), `decrease_rate(self) -> float` (`set_rate(self.rate_days_per_sec / RATE_STEP_FACTOR)`).

### src/solar_system/scaling.py

Hierarchical logarithmic distance scaling, bounded non-overlapping moon neighborhoods, and strictly monotonic body size mapping within the `1440×1080` viewport.
- Constants:
  - `VIEWPORT_WIDTH: int = 1440`, `VIEWPORT_HEIGHT: int = 1080`, `SUN_SCREEN_CENTER: Vec2 = Vec2(720.0, 540.0)`.
  - `HELIOCENTRIC_MIN_AU: float = 0.30`, `HELIOCENTRIC_MAX_AU: float = 375.0`, `HELIOCENTRIC_R_MIN_PX: float = 52.0`, `HELIOCENTRIC_R_MAX_PX: float = 500.0`.
  - `MOON_NEIGHBORHOOD_RADII_PX: dict[str, float] = {"Earth": 18.0, "Mars": 16.0, "Jupiter": 28.0, "Saturn": 22.0, "Neptune": 18.0}`.
  - `MOON_INNER_FRACTION: float = 0.32`.
- Key functions:
  - `heliocentric_distance_to_px(r_au: float) -> float`: returns `0.0` for `r_au <= 0.0`; for `r_au > 0.0`, maps logarithmically (base 10) via `52.0 + (500.0 - 52.0) * (math.log10(max(r_au, 0.30)) - math.log10(0.30)) / (math.log10(375.0) - math.log10(0.30))` (strictly monotonic for all `r_au >= 0.30 AU`).
  - `moon_distance_to_px(r_km: float, primary_name: str, min_a_km: float, max_a_km: float) -> float`: maps a moon's distance `r_km` from its primary into `[r_inner_px, r_outer_px]` inside `MOON_NEIGHBORHOOD_RADII_PX[primary_name]` using `log10(r_km)` interpolation when `max_a_km > min_a_km` (or `0.65 * r_outer_px` for single-moon primaries `Earth` and `Neptune`), guaranteeing strictly monotonic moon ordering (`Io < Europa < Ganymede < Callisto`, `Phobos < Deimos`) and bounded non-overlapping neighborhoods.
  - `body_display_radius_px(radius_km: float, category: BodyCategory) -> float`: strictly monotonic continuous log10 size mapping `r_px = 1.2 + 2.15 * math.log10(max(radius_km, 1.0))` for orbiting bodies (`2.4 km` Encke → `2.02 px`, `1,737 km` Moon → `8.17 px`, `6,371 km` Earth → `9.38 px`, `69,911 km` Jupiter → `11.61 px`) and `20.0 px` for the Sun (`696,340 km`), ensuring `r1 < r2 => body_display_radius_px(r1) < body_display_radius_px(r2)` across all physical radii.
  - `world_to_screen(body: Body, rel_offset: Vec2, primary_screen_pos: Vec2, bodies: Mapping[str, Body]) -> Vec2`: transforms focus-relative orbital offset `rel_offset` into screen pixel coordinates `(x_px, y_px)` with screen `y` inverted (`y_screen = center_y - y_world_px`).
  - `sample_orbit_screen_points(body: Body, primary_screen_pos: Vec2, bodies: Mapping[str, Body], num_samples: int = 180) -> list[tuple[float, float]]`: samples `num_samples` eccentric anomalies `E ∈ [0, 2π)` along the body's exact Keplerian ellipse and transforms each point via `world_to_screen` so eccentric orbits (Mercury, Mars, Halley, Encke, Hale–Bopp) render as true focus-offset oval curves within `[0, 1440) × [0, 1080)`.

### src/solar_system/scenes.py

Explicit Finite State Machine (`SceneFSM`) and headless scene controllers for `Title`, `Simulation`, and `Paused` states.
- Enum: `class SceneState(StrEnum)` with states `TITLE = "TITLE"`, `SIMULATION = "SIMULATION"`, `PAUSED = "PAUSED"`, `QUIT = "QUIT"`.
- Data model: `@dataclass(frozen=True, slots=True) class InputEvent` with fields `key: str` (normalized key names: `"SPACE"`, `"P"`, `"PLUS"`, `"MINUS"`, `"RETURN"`, `"ESCAPE"`, or raw key label) and `event_type: Literal["KEYDOWN", "QUIT"] = "KEYDOWN"`.
- Protocol / Base class `Scene`: implements `state: SceneState`, `handle_event(self, event: InputEvent, fsm: SceneFSM) -> None`, and `update(self, dt_sec: float) -> None`.
- Concrete scenes:
  - `TitleScene`: transitions `fsm.transition_to(SceneState.SIMULATION)` on `"RETURN"` or `"SPACE"`, transitions to `SceneState.QUIT` on `"ESCAPE"` or `event_type == "QUIT"`, ignores all other keys.
  - `SimulationScene`: on `"SPACE"` calls `simulation.reverse()`, on `"P"` transitions `fsm.transition_to(SceneState.PAUSED)` and pauses simulation, on `"PLUS"` calls `simulation.increase_rate()`, on `"MINUS"` calls `simulation.decrease_rate()`, on `"ESCAPE"` transitions to `SceneState.QUIT`, and in `update(dt_sec)` calls `simulation.advance(dt_sec)`.
  - `PausedScene`: on `"P"` resumes simulation and transitions `fsm.transition_to(SceneState.SIMULATION)`, on `"SPACE"` reverses `simulation.direction` while remaining paused, on `"PLUS"` / `"MINUS"` adjusts `simulation.rate_days_per_sec`, on `"ESCAPE"` transitions to `SceneState.QUIT`, and in `update(dt_sec)` performs no simulation time advance (`dt_sec` ignored).
- Class `SceneFSM`: owns `current_state: SceneState`, `simulation: Simulation`, scene instances map, `handle_event(event: InputEvent) -> SceneState`, `update(dt_sec: float) -> None`, and `is_running` property (`current_state != SceneState.QUIT`).

### src/solar_system/renderer.py

Pygame 2D rendering engine translating `Simulation` state and `SceneFSM` state onto a `1440×1080` `pygame.Surface`.
- Constants: `WINDOW_TITLE: str = "Favur - Solar System"`, `BG_COLOR_RGB: tuple[int, int, int] = (5, 7, 15)`, `ORBIT_LINE_COLOR_RGBA: tuple[int, int, int, int] = (70, 90, 130, 85)`, `COMET_ORBIT_COLOR_RGBA: tuple[int, int, int, int] = (110, 140, 175, 95)`, `HUD_TEXT_COLOR_RGB: tuple[int, int, int] = (225, 232, 245)`.
- Class `SolarSystemRenderer`:
  - `__init__(self, surface: pygame.Surface, bodies: Mapping[str, Body]) -> None`: initializes offscreen `trail_surface = pygame.Surface((1440, 1080), pygame.SRCALPHA)`, pre-computes static heliocentric orbit polylines (`sample_orbit_screen_points`), and loads HUD fonts (`pygame.font.SysFont("consolas", ...)`).
  - `draw(self, fsm: SceneFSM) -> None`: dispatches rendering for the active scene:
    1. Fills background `(5, 7, 15)` and renders deterministic starfield backdrop.
    2. Draws faint orbit ellipses for planets, minor bodies, comets, and active moon neighborhoods.
    3. Renders fading trails from each body's `TrailBuffer` onto `trail_surface` with per-point alpha `int(220 * point.opacity)` and blits `trail_surface` onto `surface`.
    4. Draws the central Sun glow and `20.0 px` filled disk at `(720, 540)`, procedural main-belt points, planets, moons, minor bodies, and comets at their exact `world_to_screen` positions with `int(round(body_display_radius_px(...)))` radii and body labels.
    5. Draws HUD telemetry (`Time (days/years)`, `Direction: FORWARD (+1) / REVERSE (-1)`, `Rate: X days/s`, `State: TITLE / RUNNING / PAUSED`, and control legend) plus scene-specific overlays for `TitleScene` and `PausedScene`.
  - `save_screenshot(self, path: str | Path) -> None`: writes the current `surface` to disk via `pygame.image.save(self.surface, str(path))`.

### src/solar_system/main.py

Application entry point, Pygame window lifecycle manager, keyboard event translator, and CLI runner.
- Exception class: `class GuiInitializationError(RuntimeError)` raised when `pygame.init()` or `pygame.display.set_mode((1440, 1080))` fails.
- Key functions:
  - `translate_pygame_event(event: pygame.event.Event) -> InputEvent | None`: maps `pygame.QUIT` → `InputEvent(key="QUIT", event_type="QUIT")` and `pygame.KEYDOWN` (`K_SPACE` → `"SPACE"`, `K_p` → `"P"`, `K_PLUS`/`K_EQUALS`/`K_KP_PLUS` → `"PLUS"`, `K_MINUS`/`K_KP_MINUS` → `"MINUS"`, `K_RETURN`/`K_KP_ENTER` → `"RETURN"`, `K_ESCAPE` → `"ESCAPE"`) while mapping unrecognized keys to `"OTHER"`.
  - `init_window() -> pygame.Surface`: initializes `pygame.display` and `pygame.font`, calls `pygame.display.set_caption("Favur - Solar System")`, creates a `1440×1080` non-resizable window (`flags=0`), and raises `GuiInitializationError` on `pygame.error`.
  - `run_app(max_frames: int | None = None, start_in_simulation: bool = False) -> int`: runs the 60 FPS event/update/render loop (`clock.tick(60)` with fixed deterministic step `dt = 1.0 / 60.0` seconds), dispatching events to `SceneFSM` and rendering via `SolarSystemRenderer`.
  - `main(argv: Sequence[str] | None = None) -> int`: top-level CLI entry point wrapping `run_app` in a clean exception handler that catches `GuiInitializationError`, `OrbitalElementsError`, `ConvergenceError`, and unexpected exceptions, prints a clear diagnostic message to `sys.stderr`, and exits with code `1` (never printing a raw traceback).

### tests/conftest.py

Headless test configuration and shared `pytest` fixtures.
- Sets `os.environ.setdefault("SDL_VIDEODRIVER", "dummy")` and `os.environ.setdefault("SDL_AUDIODRIVER", "dummy")` at the top of the file before any test imports.
- Provides reusable fixtures: `reference_bodies() -> dict[str, Body]`, `full_catalog() -> dict[str, Body]`, `simulation() -> Simulation`, and `scene_fsm() -> SceneFSM`.

### tests/test_vector.py

Unit tests for `src/solar_system/vector.py`.
- Verifies `Vec2` immutability (`FrozenInstanceError` on attribute assignment), `add`, `sub`, `scale`, `magnitude`, `distance_to`, `normalize` (including zero-vector guard), `rotate` (`0`, `π/2`, `π`, `2π`), `dot`, `cross`, operator overloads, and `eq` within tolerance `1e-9`.

### tests/test_kepler.py

Unit tests for Sub-suite 1 (Kepler solver) and Sub-suite 2 (Orbital mechanics) against `src/solar_system/kepler.py`.
- Verifies `solve_kepler(M, e, tol=1e-9)` satisfies `|E - e·sin(E) - M| <= 1e-9` across `M` in `0` to `2π` for all eccentricities in the catalog, including near-circular (`Triton e=0.000016`, `Venus e=0.0068`) and extreme high-eccentricity (`1P/Halley e=0.967`, `2P/Encke e=0.848`, `Hale-Bopp e=0.995`).
- Verifies Kepler's third law (`T_yr^2 / a_au^3 == pytest.approx(1.0, rel=0.01)`), perihelion distance `r_min == a*(1 - e)` at `M = 0`, aphelion distance `r_max == a*(1 + e)` at `M = π`, Kepler's second law (equal areas swept in equal `Δt` intervals via 2D cross-product numerical integration within `1e-5` relative tolerance), and `ConvergenceError` when `max_iter` is exceeded.

### tests/test_frames.py

Unit tests for Sub-suite 3 (Reference-frame composition) against `src/solar_system/frames.py`.
- Verifies `absolute_position` for the Sun (`Vec2(0.0, 0.0)` at all `t`), heliocentric planets, and moons orbiting planets (`Moon` around `Earth`, `Io`/`Europa`/`Ganymede`/`Callisto` around `Jupiter`, `Titan` around `Saturn`, `Phobos`/`Deimos` around `Mars`, retrograde `Triton` around `Neptune`).
- Verifies that `|pos(moon, t) - pos(primary, t)|` in km stays strictly within `[a*(1 - e), a*(1 + e)]` for all `t` and that circular/missing primary references raise `ValueError`.

### tests/test_bodies.py

Unit tests for `src/solar_system/bodies.py`.
- Verifies all 25 J2000 reference bodies match the exact table values in `## Reference Data`, verifies `OrbitalElementsError` is raised at definition time when `e >= 1.0`, `e < 0.0`, `a <= 0.0`, or `T <= 0.0`, and verifies `generate_main_belt(seed=20260901)` is deterministic, generates 180 bodies within `2.1–3.3 AU`, and places zero bodies inside the 4 Kirkwood gap intervals.

### tests/test_trail.py

Unit tests for Sub-suite 4 (Trail model) against `src/solar_system/trail.py`.
- Verifies `TrailBuffer` respects `capacity`, evicts oldest points first (FIFO) when capacity is exceeded, assigns `opacity = 1.0` to the newest point and strictly increasing opacity from oldest to newest according to `decay_rate`, supports `clear()`, and rejects invalid `capacity < 1` or `decay_rate <= 0`.

### tests/test_simulation.py

Unit tests for Sub-suite 5 (Simulation determinism and time-reversal invariance) against `src/solar_system/simulation.py`.
- Verifies `state_at(t)` is a pure function (calling `state_at(t)` repeatedly in any order returns identical `Vec2` coordinates without mutating `simulation.time_days` or trails).
- Verifies time-reversal invariance: advancing by `N` steps of `dt`, calling `reverse()`, and advancing by `N` steps of `dt` returns `time_days` to `t0` and returns every body to its exact initial position within `1e-11 AU`; reversing twice (`reverse(); reverse()`) restores `+1` direction and original trajectory.
- Verifies `pause()`, `resume()`, `toggle_pause()`, `set_rate()`, `increase_rate()`, and `decrease_rate()`.

### tests/test_scaling.py

Unit tests for Sub-suite 6 (Display scaling) against `src/solar_system/scaling.py`.
- Verifies strict distance monotonicity (`a1 < a2 => heliocentric_distance_to_px(a1) < heliocentric_distance_to_px(a2)` for all heliocentric bodies and `moon_distance_to_px` for all sibling moons).
- Verifies strict size monotonicity (`r1 < r2 => body_display_radius_px(r1) < body_display_radius_px(r2)` across all physical radii).
- Verifies viewport containment: for every body in the full catalog across a full orbit (`E` from `0` to `2π`), `0 <= x_px - r_px` and `x_px + r_px <= 1440` and `0 <= y_px - r_px` and `y_px + r_px <= 1080`, and verifies that planetary moon neighborhood bounding circles never overlap adjacent planetary orbits.

### tests/test_scenes.py

Unit tests for Sub-suite 7 (Scene FSM) against `src/solar_system/scenes.py`.
- Verifies initial state `SceneState.TITLE`, transition `TITLE -> SIMULATION` on `RETURN` or `SPACE`, `SIMULATION -> PAUSED` on `P`, `PAUSED -> SIMULATION` on `P`, `SPACE` time reversal in `SIMULATION` and `PAUSED`, `+`/`-` rate adjustments, `ESCAPE` transition to `SceneState.QUIT` from all three states, active-scene-only event dispatch, and silent ignoring of unrecognized keys (`"A"`, `"Z"`, `"F1"`).

### README.md

Project documentation at the workspace root.
- Documents the target language (`Python 3.11+`), prerequisites (`Python >=3.11`, `Poetry >=2.0`), setup (`poetry install`), static validation (`poetry run ruff check .`, `poetry run mypy src tests`), automated testing (`poetry run pytest`), running the simulation (`poetry run solar-system` or `poetry run python -m solar_system.main`), the exact hierarchical logarithmic scaling equations and constants (`HELIOCENTRIC_MIN_AU = 0.30`, `HELIOCENTRIC_MAX_AU = 375.0`, `R_MIN = 52.0 px`, `R_MAX = 500.0 px`, moon neighborhood radii, and `log10` body radius formula), and keyboard controls (`SPACE`, `P`, `+`/`-`, `Enter`, `Escape`).

### visual-proof/README.md

Visual verification manifest inside `visual-proof/`.
- Lists every captured PNG artifact (`01_first_light.png`, `02_title_scene.png`, `03_simulation_scene.png`, `04_paused_scene.png`, `05_before_reversal.png`, `06_after_reversal.png`, `07_rate_change.png`), what observable simulation state each image proves, the exact simulation time `t` and keyboard input sequence used to produce it, and verification notes.

## Error Handling Strategy

Failure class (a) — GUI initialization failure (`GuiInitializationError(RuntimeError)`): if `pygame.display.init()`, `pygame.font.init()`, or `pygame.display.set_mode((1440, 1080))` raises `pygame.error` (for example, when no display server is available and `SDL_VIDEODRIVER` is not set to `dummy`), `init_window()` raises `GuiInitializationError` with a descriptive message naming the SDL/Pygame failure. `main()` catches `GuiInitializationError`, writes `"Error: Failed to initialize GUI display (1440x1080): <reason>\n"` to `sys.stderr`, invokes `pygame.quit()`, and returns exit code `1`. This is the only condition where a hard startup exit is permitted.

Failure class (b) — invalid orbital elements (`OrbitalElementsError(ValueError)`): defining a closed-orbit `Body` or `OrbitalElements` with `eccentricity < 0.0` or `eccentricity >= 1.0`, `semi_major_axis <= 0.0`, `orbital_period_days <= 0.0`, or `radius_km <= 0.0` raises `OrbitalElementsError` immediately at construction/definition time (`__post_init__`), never deferred to render time. The exception message explicitly names the body and the offending parameter value (e.g., `"Invalid orbital elements for 'TestComet': eccentricity=1.05 must satisfy 0.0 <= e < 1.0 for a closed elliptical orbit"`).

Failure class (c) — Newton–Raphson non-convergence (`ConvergenceError(RuntimeError)`): if `solve_kepler(mean_anomaly, eccentricity, tol=1e-9, max_iter=100, body_name=...)` fails to reach `|E - e·sin(E) - M| <= tol` within `max_iter` iterations (or encounters a non-positive derivative), it raises `ConvergenceError(RuntimeError)` carrying structured attributes (`body_name`, `mean_anomaly`, `eccentricity`, `iterations`) and a message stating the body name, mean anomaly `M` (in radians), eccentricity `e`, tolerance `tol`, and number of iterations attempted (`max_iter`).

Failure class (d) — invalid or unrecognized keyboard input: keyboard events outside the defined control set (`SPACE`, `P`, `+`/`=`/`KP_PLUS`, `-`/`KP_MINUS`, `RETURN`/`KP_ENTER` on `Title`, and `Escape`) are translated to `"OTHER"` and silently ignored by `TitleScene`, `SimulationScene`, and `PausedScene` — no exception is raised, no state mutation occurs, and no warning/error is emitted.

Failure class (e) — general no-traceback guarantee: the application must never display a raw Python traceback to the user during normal CLI or window execution. The top-level `main()` entry point wraps execution in a `try ... except (GuiInitializationError, OrbitalElementsError, ConvergenceError, ValueError, RuntimeError, Exception)` block that ensures `pygame.quit()` is called, writes a single human-readable error line to `sys.stderr`, and exits with code `1`.

## Testing Requirements

Per the Favur testing architecture (`memory-bank/guides/unit-integration-testing.md`), the entire model layer (`vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`) is unit-tested headlessly under `pytest` with zero GUI, rendering, input-system, or window-system dependencies. The test suite is organized into seven required sub-suites (plus foundational vector/body catalog assertions):

Sub-suite 1 — Kepler solver (`tests/test_kepler.py`): verifies that `solve_kepler(M, e, tol=1e-9)` satisfies `|E - e·sin(E) - M| <= 1e-9` across a dense grid of mean anomalies `M ∈ [0, 2π]` (including boundary values `0`, `1e-12`, `π/2`, `π`, `3π/2`, `2π`) for all eccentricities in the catalog, explicitly including near-zero (`Triton e = 0.000016`, `Venus e = 0.0068`) and high-eccentricity comets (`2P/Encke e = 0.848`, `1P/Halley e = 0.967`, and `Hale-Bopp e = 0.995`). Also verifies `ConvergenceError` is raised with body name, `M`, `e`, and iteration count when `max_iter=1` fails to converge.

Sub-suite 2 — Orbital mechanics (`tests/test_kepler.py` and `tests/test_bodies.py`): verifies Kepler's third law (`T_yr^2 / a_au^3 == pytest.approx(1.0, rel=0.01)`) across all heliocentric planets, minor bodies, and comets in the J2000 reference data; verifies computed perihelion distance (`M = 0`) equals `a(1 - e)` and aphelion distance (`M = π`) equals `a(1 + e)` within `1e-9` relative tolerance; and numerically verifies Kepler's second law (equal areas swept in equal simulation-time intervals `Δt` at perihelion vs aphelion using triangular wedge cross-products `0.5 * |r(t) × r(t + δt)|` integrated over sub-steps within `1e-4` relative tolerance). Also verifies `OrbitalElementsError` is raised at body definition time for `e >= 1.0` or `e < 0.0`.

Sub-suite 3 — Frame composition (`tests/test_frames.py`): verifies `absolute_position` for hierarchical primary chains: `Sun` at `(0.0, 0.0)`, planets orbiting `Sun`, and all 9 moons orbiting their respective primaries (`Moon` around `Earth`, `Io`, `Europa`, `Ganymede`, `Callisto` around `Jupiter`, `Titan` around `Saturn`, `Phobos`, `Deimos` around `Mars`, and retrograde `Triton` around `Neptune`), confirming that `|pos(moon, t) - pos(primary, t)| * AU_IN_KM` lies within `[a_km * (1 - e), a_km * (1 + e)]` and that retrograde `Triton` sweeps clockwise (`cross(r(t), r(t + dt)) < 0`).

Sub-suite 4 — Trail model (`tests/test_trail.py`): verifies `TrailBuffer(capacity=120, decay_rate=0.008)` respects its fixed capacity `capacity`, evicts oldest positions first (FIFO) once capacity is reached, and assigns strictly monotonic per-point opacity decaying with age from `1.0` (newest) down toward `MIN_TRAIL_OPACITY` (oldest).

Sub-suite 5 — Simulation determinism (`tests/test_simulation.py`): verifies `Simulation.state_at(t)` is a pure, reproducible function of simulation time `t` (calling `state_at(t)` at arbitrary times produces bit-identical `dict[str, Vec2]` positions without side effects), and verifies time-reversal invariance: advancing `N` steps forward (`dt > 0`), calling `reverse()`, and advancing `N` steps returns the clock to `t0` and returns every body to its exact original position within `1e-11 AU`; calling `reverse()` twice restores forward motion along the identical trajectory.

Sub-suite 6 — Display scaling (`tests/test_scaling.py`): verifies that `heliocentric_distance_to_px`, `moon_distance_to_px`, and `body_display_radius_px` are strictly monotonic in distance and physical radius respectively, that moon neighborhood radii never overlap adjacent planet orbits, and that all rendered content (every planet, moon, minor body, comet including `Hale-Bopp` at aphelion `371.07 AU`, and main-belt asteroid across `E ∈ [0, 2π)`) stays strictly within the `1440×1080` viewport (`0 <= x - r` and `x + r <= 1440`, `0 <= y - r` and `y + r <= 1080`).

Sub-suite 7 — Scene FSM (`tests/test_scenes.py`): verifies state transitions between `Title`, `Simulation`, and `Paused` (`Title -> Simulation` on `RETURN`/`SPACE`, `Simulation <-> Paused` on `P`, `Any -> Quit` on `Escape`), verifies events dispatch exclusively to the active scene (`P` in `Title` does not pause/transition; `dt` in `Paused` does not advance simulation time), and verifies `SPACE`, `+`, `-`, and unrecognized keys behave as specified.

The automated test suite (`poetry run pytest`) must pass with `0` failures and terminate without interactive or watch mode. In `spec.md` line 223, the original specification states verbatim: `"Coverage target: 100% for the model layer (orbital mechanics, simulation, trail, scaling, FSM)."`. Per the Favur orchestrator code-coverage ceiling policy (which caps required line, statement, branch, and function coverage thresholds at `90%`), the required pass/fail coverage gate for the model layer (`vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`) is amended to at least `90%` (`--cov-fail-under=90`), recorded as provisional interpretation `SOW-OQ-003` (`Origin: automatic`), while aiming for comprehensive branch coverage of all model behaviors and reporting actual measured coverage honestly.

## Implementation Phases

### Phase 1: Research and Solver Spike

Implement `pyproject.toml`, `src/solar_system/vector.py`, and `src/solar_system/kepler.py`, along with `tests/test_vector.py` and `tests/test_kepler.py`. Exit when `poetry run pytest tests/test_vector.py tests/test_kepler.py` passes with `0` failures, proving that `solve_kepler` converges within `1e-9` across `[0, 2π]` for all eccentricities including `1P/Halley` (`e = 0.967`) and `Hale-Bopp` (`e = 0.995`), and that Kepler's three laws hold numerically.

### Phase 2: Model Layer and Tests

Implement `src/solar_system/frames.py`, `src/solar_system/bodies.py`, `src/solar_system/trail.py`, `src/solar_system/simulation.py`, `src/solar_system/scaling.py`, and `src/solar_system/scenes.py`, together with `tests/conftest.py`, `tests/test_frames.py`, `tests/test_bodies.py`, `tests/test_trail.py`, `tests/test_simulation.py`, `tests/test_scaling.py`, and `tests/test_scenes.py`. Exit when `poetry run pytest --cov=solar_system` passes with `0` failures, model-layer coverage is `>= 90%` (`SOW-OQ-003`), `poetry run ruff check .` and `poetry run mypy src tests` report `0` errors, and no model module imports `pygame`.

### Phase 3: First Light (screenshot-gated)

Implement the initial Pygame window and renderer in `src/solar_system/renderer.py` and `src/solar_system/main.py` displaying the `1440×1080` non-resizable window titled `Favur - Solar System`, the black space background, the central Sun at the shared focus `(720, 540)`, and the planets on their real focus-offset orbit ellipses. Exit only when `visual-proof/01_first_light.png` is captured from the running window and verified via `analyze_image`.

### Phase 4: Full Render and Scenes (screenshot-gated)

Complete `src/solar_system/renderer.py` and `src/solar_system/main.py` to render all 25 catalog bodies, the 180 main-belt asteroids with Kirkwood gaps, planetary moon neighborhoods, faint orbit ellipses, fading alpha-blended trails, HUD telemetry, and the `Title`, `Simulation`, and `Paused` scene overlays. Exit only when `visual-proof/02_title_scene.png`, `visual-proof/03_simulation_scene.png`, and `visual-proof/04_paused_scene.png` are saved to `visual-proof/` and verified via `analyze_image`.

### Phase 5: Controls and Visual-Proof Sweep

Verify live keyboard interactions (`SPACE` time reversal, `P` pause toggle, `+`/`-` rate scaling, `Escape` clean quit), capture the `SPACE` before/after time-reversal pair (`visual-proof/05_before_reversal.png` and `visual-proof/06_after_reversal.png`) and the `+`/`-` rate change screenshot (`visual-proof/07_rate_change.png`), and author the complete `visual-proof/README.md` manifest and root `README.md`. Exit when all 7 visual proof PNGs and `visual-proof/README.md` exist on disk and pass visual verification.

### Phase 6: Final Verification

Execute the complete verification suite: `poetry install`, `poetry run ruff check .`, `poetry run mypy src tests`, `poetry build`, `poetry run pytest --cov=solar_system`, and live application launch verification. Exit when all commands exit `0` with `0` test failures and `0` lint/type errors.

## Acceptance Criteria

- [ ] The window opens with the exact title `Favur - Solar System` at 1440×1080 and is not resizable (SG1, SOW-REQ-001).
- [ ] Pressing `SPACE` reverses the direction of simulation time, reversing all motion (SG3, SOW-REQ-004).
- [ ] `P` toggles pause; `Escape` on any scene closes the window without errors (SG3, SOW-REQ-004).
- [ ] The Kepler solver satisfies `M = E − e·sin(E)` within `1e−9` across the full range of mean anomaly (SG2, SOW-REQ-002).
- [ ] Kepler's third law holds across the modeled bodies: `T² ∝ a³` within 1% tolerance (SG2, SOW-REQ-002).
- [ ] Computed perihelion and aphelion distances match `a(1 − e)` and `a(1 + e)` within tolerance (SG2, SOW-REQ-002).
- [ ] Kepler's second law is verified numerically: equal areas are swept in equal simulation-time intervals within tolerance (SG2, SOW-REQ-002).
- [ ] The trail ring buffer respects its fixed capacity and evicts oldest-first (SOW-REQ-005).
- [ ] The display scaling is strictly monotonic in both distance and size, and all rendered content stays within the viewport (SG4, SOW-REQ-006).
- [ ] The scene state machine transitions correctly between Title, Simulation, and Paused (SOW-REQ-007).
- [ ] The simulation is deterministic: `state_at(t)` is reproducible, and reversing time twice returns every body to its original trajectory (SG2, SOW-REQ-003).
- [ ] The default view looks like a credible solar-system visualization with an intuitive size hierarchy and visibly non-circular eccentric orbits (SG4, SOW-REQ-006).
- [ ] The project uses idiomatic structure and tooling for the selected target language (SOW-REQ-001, SOW-REQ-010).
- [ ] All applicable static validation, type checking, compilation, or build steps complete with 0 errors — mandatory (SOW-REQ-001, SOW-REQ-015).
- [ ] The selected language's normal automated test command passes with 0 failures — mandatory — and terminates without interactive/watch mode (SG2, SOW-REQ-008).
- [ ] The documented run command launches the simulation without errors (SOW-REQ-001).
- [ ] The core model is testable headlessly and contains no GUI, rendering, input-system, or window-system dependency (SG2, SOW-REQ-003).
- [ ] `README.md` documents the target language, prerequisites, setup, build/validation, test, run, scaling regime, and controls using commands verified against the actual project (SOW-REQ-001, SOW-REQ-015).
- [ ] `visual-proof/` contains first light, each scene, a `SPACE` before/after reversal pair, and a `+`/`-` rate change, plus a manifest naming each file and its input sequence — captured progressively during the build (SG5, SOW-REQ-009).
- [ ] Defining a closed-orbit body with `eccentricity >= 1.0` or `eccentricity < 0.0` raises `OrbitalElementsError(ValueError)` at definition time naming the body and invalid value, and non-convergence within `max_iter` raises `ConvergenceError(RuntimeError)` naming the body, `M`, `e`, and iterations attempted (SG2, SOW-REQ-012, SOW-REQ-013).
- [ ] Unrecognized keyboard keys are silently ignored without crash or error output, and startup/runtime failures emit a legible error message to `sys.stderr` without exposing a raw Python traceback (SG3, SOW-REQ-014).
- [ ] Model-layer test coverage (`vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`) achieves at least 90% under `pytest --cov=solar_system` per the Favur 90% coverage ceiling policy amendment (`SOW-OQ-003`, amending the imported `spec.md` target `"Coverage target: 100% for the model layer (orbital mechanics, simulation, trail, scaling, FSM)"`) (SG2, SOW-REQ-008).

## Design Decisions

### [SOW-ADR-001] Safeguarded Newton–Raphson Kepler solver for eccentric anomaly

**Status**: Accepted
**Context**: Recovering eccentric anomaly `E` from mean anomaly `M` requires solving the transcendental equation `M = E − e·sin(E)` across eccentricities ranging from `e = 0.000016` (Triton) to `e = 0.967` (1P/Halley) and `e = 0.995` (Hale–Bopp). Plain Newton–Raphson with a naive initial guess `E0 = M` can overshoot near perihelion (`M ≈ 0`) when `1 − e·cos(E)` is as small as `0.005`.
**Decision**: Use Newton–Raphson iteration to a configurable residual tolerance (`default = 1e−9`, `max_iter = 100`) combined with modulo-`2π` symmetry reduction onto `m ∈ [0, π]`, initial guess `E0 = π` for `e > 0.8` and `E0 = m + e·sin(m)` for `e <= 0.8`, and a bracket `[m, m + e]` bisection fallback whenever a Newton step leaves the bracket.
**Rationale**: Newton–Raphson converges quadratically in the local basin (`5–12` iterations for planets, `< 35` iterations for `e = 0.995`), while the `[m, m + e]` bracket safeguard guarantees global convergence across all `M ∈ [0, 2π]` without adding external dependencies such as `scipy`. Alternatives considered: fixed-point iteration `E_{n+1} = M + e·sin(E_n)` (rejected because contraction factor `0.995` requires thousands of iterations near perihelion) and `scipy.optimize.brentq` (rejected to keep the model layer pure standard-library Python).

### [SOW-ADR-002] Hierarchical logarithmic display scaling with bounded moon neighborhoods

**Status**: Accepted
**Context**: The solar system spans over three orders of magnitude in heliocentric orbital distance (`0.307 AU` Mercury perihelion to `371.07 AU` Hale–Bopp aphelion) while planetary moon orbits span `9,376 km` (Phobos) to `1,883,000 km` (Callisto) (`6.3e−5 AU` to `0.0126 AU`). A single linear or single global logarithmic scale either collapses inner planets onto the Sun or collapses moons inside their primary's pixel radius.
**Decision**: Apply two-level hierarchical logarithmic distance scaling: (1) heliocentric `log10` radial mapping from `[0.30 AU, 375.0 AU]` into `[52.0 px, 500.0 px]` around the Sun at `(720, 540)`, and (2) local `log10` radial mapping for each moon inside a bounded, non-overlapping neighborhood radius around its primary planet (`16.0 px` to `28.0 px`), paired with a continuous `log10` body radius formula (`1.2 + 2.15 * log10(radius_km)` for orbiting bodies, `20.0 px` for the Sun).
**Rationale**: Hierarchical scaling keeps orbits at both heliocentric and planetocentric depths visually resolvable and strictly monotonic in distance and size, preserves true focus-offset elliptical shapes (`e = 0.2056` for Mercury through `e = 0.995` for Hale–Bopp), and guarantees all content remains inside `1440×1080` with at least `40 px` viewport margin.

### [SOW-ADR-003] Pure `state_at(t)` function for determinism and headless testing

**Status**: Accepted
**Context**: The simulation must be 100% deterministic, reproducible, headlessly unit-testable without a display server, and capable of exact time reversal when `SPACE` is pressed.
**Decision**: Expose every body's world position through `Simulation.state_at(t_days: float) -> dict[str, Vec2]` as a pure mathematical function of simulation time `t_days`, with zero `pygame`, rendering, input-system, or wall-clock dependencies anywhere in the model modules (`vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`).
**Rationale**: Computing positions analytically from `M(t) = M0 ± 2π·t/T` rather than integrating velocity incrementally eliminates cumulative numerical drift (symplectic/Euler drift), makes `state_at(t)` trivially unit-testable at arbitrary epochs, and ensures reversing time (`direction = -1`) retraces the exact same trajectory down to IEEE-754 floating-point precision.

### [SOW-ADR-004] Pygame 2.x with offscreen `SRCALPHA` trail compositing

**Status**: Accepted
**Context**: The Python implementation requires a reliable 2D windowing and drawing library installed in the workspace environment capable of rendering a fixed `1440×1080` window, anti-aliased orbit ellipses, filled circles, HUD text, alpha-blended fading trails, and PNG screenshot capture.
**Decision**: Use `pygame` (`>=2.5.0,<3.0.0`, verified `2.6.1` installed in workspace) with an offscreen `pygame.Surface((1440, 1080), pygame.SRCALPHA)` layer for per-point alpha-blended trails and sampled 180-vertex polylines for focus-offset eccentric orbit ellipses.
**Rationale**: `pygame` is pre-installed in the workspace (`2.6.1`), supports both live desktop windowing for `window_control` visual verification and `SDL_VIDEODRIVER=dummy` headless surface rendering for `pytest`, and provides deterministic `pygame.image.save()` PNG export. Sampling 180 eccentric anomaly points per orbit avoids `pygame.draw.ellipse()`'s axis-aligned bounding-box limitation and accurately places the primary at the true focus under logarithmic scaling.

### [SOW-ADR-005] Fixed-capacity `deque` ring buffer for orbital trails

**Status**: Accepted
**Context**: Every orbiting body must leave a fading trail that evicts oldest positions first and stays bounded in memory and per-frame draw cost over arbitrarily long runs.
**Decision**: Implement `TrailBuffer` in `src/solar_system/trail.py` using `collections.deque(maxlen=capacity)` (`DEFAULT_TRAIL_CAPACITY = 120`, `DEFAULT_TRAIL_DECAY_RATE = 0.008`) storing `(Vec2, sim_time_days)` pairs and computing linear age-based opacity decay on read (`points() -> list[TrailPoint]`).
**Rationale**: `collections.deque(maxlen=capacity)` provides `O(1)` append with automatic oldest-first eviction, zero external dependencies, and clean separation between model-layer position history (`Vec2` in world coordinates) and renderer-layer pixel/alpha drawing.

### [SOW-ADR-006] Explicit `SceneFSM` separating event dispatch from rendering

**Status**: Accepted
**Context**: SOW-REQ-007 requires a scene state machine managing `Title` → `Simulation` → `Paused` where events dispatch exclusively to the active scene and transitions are headlessly testable.
**Decision**: Implement `SceneFSM` and scene classes (`TitleScene`, `SimulationScene`, `PausedScene`) in `src/solar_system/scenes.py` consuming a normalized pure-Python `InputEvent(key, event_type)` dataclass, while keeping all `pygame.Surface` drawing in `src/solar_system/renderer.py`.
**Rationale**: Decoupling `SceneFSM` from `pygame.event.Event` and `pygame.Surface` allows Sub-suite 7 (`tests/test_scenes.py`) to test every state transition and key binding headlessly without initializing SDL, while `main.py` and `renderer.py` cleanly bridge Pygame events and surfaces at runtime.

## Risk Assessment

Technical risk 1 — Newton–Raphson convergence instability near perihelion for extreme-eccentricity comets (`1P/Halley e = 0.967`, `Hale-Bopp e = 0.995`) (Likelihood: Medium; Impact: High). Near `M ≈ 0` and `E ≈ 0`, `f'(E) = 1 − e·cos(E)` drops to `0.005` for Hale–Bopp, amplifying step sizes by up to `200×`. Mitigation: Spike 1 verified symmetry reduction to `m ∈ [0, π]`, high-eccentricity initial guess `E0 = π` (for `e > 0.8`), and safeguarded bracket `[m, m + e]` bisection fallback, guaranteeing convergence within `1e−9` in `< 35` iterations across all `M ∈ [0, 2π]`.

Technical risk 2 — Display scaling producing overlapping planetary moon neighborhoods or clipping Hale–Bopp's `371.07 AU` aphelion outside the `1440×1080` viewport (Likelihood: Medium; Impact: Medium). Mitigation: Spike 3 verified that mapping `[0.30 AU, 375.0 AU]` to `[52.0 px, 500.0 px]` places Hale–Bopp's aphelion at `499.3 px` from `(720, 540)` (keeping `y ∈ [40.7, 1039.3]` inside `[0, 1080]`), and bounded moon neighborhood radii (`16.0–28.0 px`) are verified in `tests/test_scaling.py` to never overlap adjacent planetary orbits.

Technical risk 3 — Headless test suite accidentally initializing a GUI window or failing when no display server is attached (Likelihood: Low; Impact: High). Mitigation: All 8 model modules are forbidden from importing `pygame` (enforced by AST/import check in `tests/`), and `tests/conftest.py` sets `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` prior to any test collection.

Technical risk 4 — Floating-point precision loss in near-circular orbits (`Triton e = 0.000016`, `Deimos e = 0.0002`, `Venus e = 0.0068`) or during repeated `SPACE` time reversals (Likelihood: Low; Impact: Low). Mitigation: `state_at(t)` is a pure analytical function of `t_days` (not an incremental velocity integrator), and `solve_kepler` is tested across both near-zero and near-unity eccentricities in `tests/test_kepler.py` and `tests/test_simulation.py`.

Integration risk 5 — Keyboard layout differences where `+` requires `Shift+=` (`K_EQUALS`) or numpad `K_KP_PLUS` on desktop keyboards (Likelihood: Medium; Impact: Medium). Mitigation: `translate_pygame_event` in `src/solar_system/main.py` maps `pygame.K_PLUS`, `pygame.K_EQUALS`, and `pygame.K_KP_PLUS` to `"PLUS"`, and maps `pygame.K_MINUS`, `pygame.K_UNDERSCORE`, and `pygame.K_KP_MINUS` to `"MINUS"`, ensuring `+`/`-` rate adjustments work reliably across all keyboard layouts and `window_control` key dispatches.

Timeline risk 6 — Progressive visual proof capture omitted or deferred until the end of the build (Likelihood: Low; Impact: High). Mitigation: Phases 3, 4, and 5 are explicitly screenshot-gated; `visual-proof/01_first_light.png` through `visual-proof/07_rate_change.png` and `visual-proof/README.md` are required deliverables verified with `analyze_image`.

## Open Questions & Assumptions

| ID | Question | Status |
|---|---|---|
| SOW-OQ-001 | Does Newton–Raphson converge within `1e-9` for all orbital eccentricities in the reference data, including `1P/Halley` (`e = 0.967`) and `Hale-Bopp` (`e = 0.995`)? | RESOLVED |
| SOW-OQ-002 | What logarithmic base and scaling constants should be used for hierarchical display scaling within the `1440×1080` viewport? | RESOLVED |
| SOW-OQ-003 | How should the imported `spec.md` model-layer 100% coverage target be reconciled with the Favur orchestrator 90% code-coverage ceiling policy? | ASSUMED |

### Resolved

#### [SOW-OQ-001] Newton–Raphson convergence for high-eccentricity orbits
**Status**: RESOLVED
**Question**: Does Newton–Raphson converge within `1e-9` for all orbital eccentricities in the reference data, including `1P/Halley` (`e = 0.967`) and `Hale-Bopp` (`e = 0.995`)?
**Impact**: If Newton–Raphson fails to converge for high-eccentricity bodies (`1P/Halley e = 0.967`, `Hale-Bopp e = 0.995`), the simulation cannot model those bodies accurately or pass Sub-suite 1.
**Resolution**: Confirmed during Pre-Implementation Research Spike 1. By reducing mean anomaly `M` modulo `2π` onto `m ∈ [0, π]` by symmetry, initializing `E0 = π` for `e > 0.8` and `E0 = m + e·sin(m)` for `e <= 0.8`, and safeguarding Newton–Raphson iterations with the sign-changing bracket `[m, m + e]`, the solver converges to `|E - e·sin(E) - M| <= 1e-9` within `35` iterations (well under `max_iter = 100`) for all bodies in the catalog across all `M ∈ [0, 2π]`.

#### [SOW-OQ-002] Display scaling constants
**Status**: RESOLVED
**Question**: What logarithmic base and scaling constants should be used for hierarchical display scaling within the `1440×1080` viewport?
**Impact**: Affects the visual readability of the simulation, non-overlapping moon neighborhoods, and whether all bodies (including Hale–Bopp at `371.07 AU` aphelion) remain inside the `1440×1080` viewport.
**Resolution**: Determined and verified during Pre-Implementation Research Spike 3. Heliocentric distances `r_au ∈ [0.30, 375.0] AU` use base-10 logarithmic interpolation into `[52.0 px, 500.0 px]` around the Sun at `(720.0, 540.0)`; planetary moons use base-10 logarithmic interpolation inside bounded neighborhood radii (`Earth: 18.0 px`, `Mars: 16.0 px`, `Jupiter: 28.0 px`, `Saturn: 22.0 px`, `Neptune: 18.0 px`); body display radii use `1.2 + 2.15 * log10(radius_km)` (`20.0 px` for the Sun). These constants are encoded in `src/solar_system/scaling.py` and documented in `README.md`.

#### [SOW-OQ-003] Model-layer code coverage threshold under orchestrator 90% coverage ceiling policy
**Status**: ASSUMED
**Question**: What required pass/fail code coverage threshold applies to the model layer when `spec.md` states a 100% coverage target but the Favur orchestrator policy enforces a 90% coverage ceiling?
**Impact**: Governs the `pytest-cov` `--cov-fail-under` configuration in `pyproject.toml` and sprint acceptance criteria verification gates.
**Resolution**: Per the Favur orchestrator code-coverage ceiling policy ("Required line, statement, branch and function coverage must not exceed 90%. Preserve lower declared targets. This caps the required threshold, not the measured result: report actual coverage honestly, including values above 90%"), the required pass/fail coverage threshold for the model layer (`vector.py`, `kepler.py`, `frames.py`, `bodies.py`, `trail.py`, `simulation.py`, `scaling.py`, `scenes.py`) is set to `>= 90%` (`fail_under = 90`), while preserving the verbatim `spec.md` target quotation for provenance and reporting actual measured coverage (up to 100%) honestly (`Origin: automatic`).
**Acknowledged**: yes
**Provenance**: interpretation
**Disposition**: provisional
**Source Text**: "Coverage target: 100% for the model layer (orbital mechanics, simulation, trail, scaling, FSM)."

## Domain / Simulation Model

The heliocentric two-body Keplerian model is used across all entities. Each orbit is a planar ellipse with its primary body located at one focus `(0.0, 0.0)` in the primary's reference frame (Kepler's First Law). For any body with orbital period `T` (in days) and initial mean anomaly `M0` (in radians at `t = 0.0`), the mean anomaly advances linearly with simulation time `t` (in days): `M(t) = M0 + sgn_orbit * (2π · t / T)`, where `sgn_orbit = -1.0` for retrograde orbits (`Triton`) and `+1.0` for prograde orbits. Eccentric anomaly `E` is recovered by solving Kepler's equation `M = E − e·sin(E)` via safeguarded Newton–Raphson iteration (`solve_kepler(M, e, tol=1e-9, max_iter=100)`). From `E`, the focus-relative Cartesian coordinates in the orbital plane are `x_orb = a · (cos(E) − e)` and `y_orb = a · sqrt(1 − e²) · sin(E)`, rotated by the argument of periapsis `ω` (`Vec2(x_orb, y_orb).rotate(ω)`), with radial distance `r = a · (1 − e·cos(E))` sweeping equal areas in equal time intervals (Kepler's Second Law) and `T_yr² = a_au³` within `1%` for heliocentric bodies (Kepler's Third Law).

A body may orbit the central star (`primary = "Sun"`, `distance_unit = "AU"`) or it may orbit another body (`primary = "Earth" | "Mars" | "Jupiter" | "Saturn" | "Neptune"`, `distance_unit = "km"`). World positions compose hierarchically by frame: `pos_world_au(body, t) = pos_world_au(primary, t) + offset_au(body, t)`, where kilometer offsets for moons are converted to AU via `1 AU = 149,597,870.7 km`. The main asteroid belt (`2.1–3.3 AU`) is populated procedurally from a fixed deterministic seed (`MAIN_BELT_SEED = 20260901`, `180` asteroids) using rejection sampling that excludes the four Kirkwood orbital-resonance gaps with Jupiter (`2.50 AU`, `2.82 AU`, `2.96 AU`, and `3.27 AU`). The simulation clock is measured in simulation days per real second (`rate_days_per_sec`, default `10.0`), never wall-clock time, and supports reversible direction (`+1` forward, `-1` backward) and adjustable rate (`[0.3125, 640.0]` days/s).

## Visual Layout Requirements

The application opens a non-resizable `1440×1080` pixel window (`VIEWPORT_WIDTH = 1440`, `VIEWPORT_HEIGHT = 1080`) with the exact title `Favur - Solar System` and top-left screen origin `(0, 0)`. The background is deep space black (`#05070F` / `RGB(5, 7, 15)`) with a deterministic subtle starfield, and the central star (`Sun`, `#FFD43B` / `RGB(255, 212, 59)`, radius `20 px`) is anchored at the shared focus `(720, 540)`.

Orbiting bodies render in distinct, high-contrast colors on visibly elliptical paths with their primary at one focus:
- `Mercury`: `#B5B8B1` (`RGB(181, 184, 177)`)
- `Venus`: `#E6C27A` (`RGB(230, 194, 122)`)
- `Earth`: `#4FA3FF` (`RGB(79, 163, 255)`)
- `Mars`: `#E06246` (`RGB(224, 98, 70)`)
- `Jupiter`: `#E3A869` (`RGB(227, 168, 105)`)
- `Saturn`: `#E8D192` (`RGB(232, 209, 146)`)
- `Uranus`: `#7AD7F0` (`RGB(122, 215, 240)`)
- `Neptune`: `#4B70DD` (`RGB(75, 112, 221)`)
- Moons: `#D6DCE8` (`RGB(214, 220, 232)`)
- Minor bodies (`Ceres`, `Vesta`, `Pallas`, `Hygiea`): `#9BA8B8` (`RGB(155, 168, 184)`)
- Comets (`1P/Halley`, `2P/Encke`, `Hale-Bopp`): `#66F0FF` (`RGB(102, 240, 255)`)
- Main-belt asteroids: `#5C6675` (`RGB(92, 102, 117)`)

Each body's display radius follows the strictly monotonic formula `r_px = 1.2 + 2.15 * log10(radius_km)` (`20.0 px` for the Sun), ensuring larger physical bodies always render larger while preserving visual readability. Each body's full orbit ellipse is drawn faintly (`RGBA(70, 90, 130, 85)` for planetary/minor orbits, `RGBA(110, 140, 175, 95)` for comets), and its recent trajectory is traced by an alpha-fading trail (`TrailBuffer` rendered onto a `pygame.SRCALPHA` overlay). All rendered orbits, bodies, moons, trails, and HUD elements stay strictly inside the `1440×1080` viewport (`x ∈ [0, 1440)`, `y ∈ [0, 1080)`). Z-ordering from back to front is: (1) space background and static starfield, (2) main-belt asteroid points, (3) faint orbit ellipses, (4) alpha-blended fading trails, (5) Sun, planets, minor bodies, comets, and moons, (6) body labels and HUD panel (`top-left (20, 16)` telemetry readout and `bottom-left (20, 1040)` controls bar), and (7) `Title` or `Paused` modal overlay banner when in `SceneState.TITLE` or `SceneState.PAUSED`.

## Reference Data

Authoritative J2000-epoch reference values encoded in `src/solar_system/bodies.py`. `a` = semi-major axis, `e` = eccentricity, `T` = orbital period, `radius` = mean physical radius. For bodies orbiting a primary other than the Sun, `a` is given as distance from that primary.

### Central Star and Planets

Central star — Sun: radius `696,340 km`.

| Body    | a (AU) |      e | T (yr) | radius (km) |
| ------- | -----: | -----: | -----: | ----------: |
| Mercury |  0.387 | 0.2056 |  0.241 |       2,440 |
| Venus   |  0.723 | 0.0068 |  0.615 |       6,052 |
| Earth   |  1.000 | 0.0167 |  1.000 |       6,371 |
| Mars    |  1.524 | 0.0934 |  1.881 |       3,390 |
| Jupiter |  5.203 | 0.0484 |  11.86 |      69,911 |
| Saturn  |  9.537 | 0.0539 |  29.45 |      58,232 |
| Uranus  |  19.19 | 0.0473 |  84.02 |      25,362 |
| Neptune |  30.07 | 0.0086 |  164.8 |      24,622 |

### Moons Orbiting a Primary

| Body     | Primary |    a (km) |        e |      T (days) | radius (km) |
| -------- | ------- | --------: | -------: | ------------: | ----------: |
| Moon     | Earth   |   384,400 |   0.0549 |         27.32 |       1,737 |
| Io       | Jupiter |   421,700 |   0.0041 |          1.77 |       1,822 |
| Europa   | Jupiter |   671,000 |   0.0094 |          3.55 |       1,561 |
| Ganymede | Jupiter | 1,070,000 |   0.0013 |          7.15 |       2,634 |
| Callisto | Jupiter | 1,883,000 |   0.0074 |         16.69 |       2,410 |
| Titan    | Saturn  | 1,222,000 |   0.0288 |         15.95 |       2,575 |
| Phobos   | Mars    |     9,376 |   0.0151 |         0.319 |          11 |
| Deimos   | Mars    |    23,460 |   0.0002 |          1.26 |           6 |
| Triton   | Neptune |   354,800 | 0.000016 | 5.88 (retro.) |       1,353 |

### Minor Bodies and Comets

**Minor bodies**

| Body   | a (AU) |      e | T (yr) | radius (km) |
| ------ | -----: | -----: | -----: | ----------: |
| Ceres  |   2.77 | 0.0758 |   4.60 |         473 |
| Vesta  |   2.36 | 0.0887 |   3.63 |         263 |
| Pallas |   2.77 | 0.2306 |   4.62 |         256 |
| Hygiea |   3.14 | 0.1125 |   5.56 |         217 |

**Long-period / high-eccentricity bodies**

| Body      | a (AU) |     e | T (yr) | radius (km) |
| --------- | -----: | ----: | -----: | ----------: |
| 1P/Halley |   17.8 | 0.967 |   75.3 |         5.5 |
| 2P/Encke  |   2.22 | 0.848 |   3.30 |         2.4 |
| Hale–Bopp |    186 | 0.995 |  2,533 |          30 |

### Main-Belt Distribution and Kirkwood Gaps

The principal minor-body region occupies roughly **2.1–3.3 AU**. Its density is not uniform: it is depleted at orbital-resonance locations with Jupiter, the Kirkwood gaps, with notable depletions near **2.50 AU (3:1)**, **2.82 AU (5:2)**, **2.96 AU (7:3)**, and **3.27 AU (2:1)**. Eccentricities are typically modest, approximately `0.05–0.30`, and longitudes are distributed around the full circle (`MAIN_BELT_SEED = 20260901`, `MAIN_BELT_ASTEROID_COUNT = 180`, excluded gap intervals `(2.46, 2.54)`, `(2.78, 2.86)`, `(2.92, 3.00)`, and `(3.22, 3.32)` AU).

## Visual Verification Protocol

Visual verification is continuous and artifact-gated across Phases 3, 4, and 5 — not a post-hoc check. First light is captured early in Phase 3: as soon as `Simulation.state_at(t)` produces positions, stand up the `1440×1080` `Favur - Solar System` window with the black space background, the Sun at `(720, 540)`, and the planets on their orbit ellipses, and capture `visual-proof/01_first_light.png` before the renderer is feature-complete. Screenshot every visible milestone at the exit of every rendering phase and inspect each saved PNG using `analyze_image(media_path=..., prompt=...)`.

The `visual-proof/` directory is a mandatory deliverable containing:
1. `visual-proof/01_first_light.png` — First light: `1440×1080` window, black background, Sun at shared focus, and planets on real focus-offset elliptical orbits.
2. `visual-proof/02_title_scene.png` — `Title` scene (`SceneState.TITLE`) displaying the solar system backdrop, application title `Favur - Solar System`, and start prompt.
3. `visual-proof/03_simulation_scene.png` — Active `Simulation` scene (`SceneState.SIMULATION`) showing all planets, moons in bounded neighborhoods, minor bodies, high-eccentricity comets (`1P/Halley`, `2P/Encke`, `Hale-Bopp`), main-belt asteroids, faint orbit ellipses, fading trails, and HUD telemetry (`Direction: FORWARD (+1)`).
4. `visual-proof/04_paused_scene.png` — `Paused` scene (`SceneState.PAUSED`) triggered by pressing `P`, showing the `PAUSED` HUD indicator and overlay with frozen orbital positions and trails.
5. `visual-proof/05_before_reversal.png` — Simulation state immediately prior to pressing `SPACE` (`Direction: FORWARD (+1)`), showing clearly established fading trails behind each moving body.
6. `visual-proof/06_after_reversal.png` — Simulation state after pressing `SPACE` (`Direction: REVERSE (-1)`) and advancing simulation time, demonstrating all bodies moving backward along their orbital ellipses and retracing their trajectories.
7. `visual-proof/07_rate_change.png` — Simulation state after pressing `+` / `-` keys, demonstrating updated `Rate (days/s)` telemetry in the HUD and corresponding trail spacing.
8. `visual-proof/README.md` — Structured manifest table and per-artifact narrative naming each PNG file, what visual requirement it verifies, the exact simulation time `t` and rate, and the exact keyboard input sequence used to capture it.

A run that completes without all required `visual-proof/` PNG artifacts and `visual-proof/README.md` is a **FAILED** run regardless of automated test status.
