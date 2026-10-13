# Statement of Work — Solar System Simulation

**Version:** 4.0 · **Date:** September 2026 · **Status:** Final

> You are building a new, standalone project from this specification. You are tasked with completing this Statement of Work **fully and completely**. While working, keep these key facts in mind:
>
> * This is a **greenfield project** — there is no existing code. Build it from scratch and do not add unrelated features.
> * Implement the project in the **target language selected for the run**.
> * Supported target languages are: **Python, TypeScript, JavaScript, Go, Rust, C#, Java, C, and C++**.
> * Use the target language's normal, idiomatic project layout, dependency management, build tooling, and test tooling.
> * Choose an appropriate GUI/windowing and 2D drawing approach for the target language and environment.
> * **Verify the real APIs and toolchain before writing code** — inspect the installed compiler/interpreter/runtime, dependency versions, and relevant GUI APIs rather than coding against remembered interfaces.
> * **Separate animation/state logic from rendering and window management** so the behavior can be unit-tested without opening a GUI.
> * **Verify your own work** — build or validate the project, run the tests, launch the application, exercise the required keyboard interactions, and capture visual proof.
> * **Complete every acceptance criterion.** Partial completion is not "done."
> * Maintain a calm and professional demeanor.

## Overview

Build an accurate, interactive 2D graphical model of the solar system in the selected target language. Bodies move on real elliptical orbits derived from published orbital elements and Kepler's laws, the Sun anchored at the shared focus. The app is scene-managed, every orbiting body leaves a fading trail, and pressing `SPACE` reverses the direction of simulation time so the whole system runs backward. The model must be deterministic: every body's position is a pure function of simulation time, so the simulation is exactly reproducible and unit-testable. Accuracy is defined precisely by the Newton–Raphson Kepler solver method, not by visual approximation. The target user is a Favur evaluator verifying that the agent can implement a physically accurate, deterministic simulation with a clean model/rendering separation.

## Goals

- **SG1**: Deliver a working interactive solar system simulation with real elliptical orbits derived from published orbital elements and Kepler's laws.
- **SG2**: Implement a deterministic model layer where every body's position is a pure function of simulation time, fully unit-testable headlessly.
- **SG3**: Support `SPACE` to reverse simulation time, `P` to toggle pause, `+`/`-` to adjust rate, and `Escape` to quit.
- **SG4**: Implement hierarchical display scaling (logarithmic distance, bounded neighborhoods, visually credible size hierarchy) that keeps all content within the 1440×1080 viewport.
- **SG5**: Produce visual proof artifacts demonstrating the running simulation and time reversal.

## Requirements

| ID | Requirement | Priority |
|---|---|---|
| SOW-REQ-001 | The window title is exactly `Favur - Solar System`; the drawable area is exactly 1440×1080, non-resizable. | Critical |
| SOW-REQ-002 | Each orbit is an ellipse with its primary at one focus; mean anomaly advances linearly with simulation time; eccentric anomaly is recovered by Newton–Raphson to a configurable tolerance. | Critical |
| SOW-REQ-003 | `state_at(t)` is a pure function of simulation time — same `t` yields identical position — with no GUI, rendering, or window-system dependency. | Critical |
| SOW-REQ-004 | `SPACE` reverses the direction of simulation time; `P` toggles pause; `+`/`-` raise and lower the simulation rate; `Escape` closes the window gracefully. | Critical |
| SOW-REQ-005 | Each orbiting body leaves a fading trail backed by a fixed-capacity ring buffer of recent positions. | High |
| SOW-REQ-006 | Display scaling is hierarchical logarithmic distance mapping with bounded non-overlapping neighborhoods and a visually credible monotonic size hierarchy; all rendered content stays within the viewport. | High |
| SOW-REQ-007 | A scene state machine manages Title → Simulation → Paused; events dispatch to the active scene. | High |
| SOW-REQ-008 | The automated test suite passes with 0 failures — mandatory — and terminates without interactive/watch mode. | Critical |
| SOW-REQ-009 | `visual-proof/` contains first light, each scene, a `SPACE` before/after reversal pair, and a `+`/`-` rate change, plus a manifest. | High |
| SOW-REQ-010 | The project uses idiomatic structure and tooling for the selected target language. | Medium |

## Reference Documents & File Locations

- Documentation for the installed target-language toolchain.
- Documentation for any GUI, rendering, build, dependency, or testing APIs selected by the implementation.
- Favur testing architecture guide: `memory-bank/guides/unit-integration-testing.md`.
- This SOW template: `tests/e2e/fixtures/specs/_SOW_TEMPLATE.md`.

## Working Agreement

This is a greenfield project. The implementation must use the target language selected for the run. The project follows the target language's normal, idiomatic project layout, dependency management, build tooling, and test tooling. The window title must be exactly `Favur - Solar System` and the drawable area must be exactly 1440×1080 and non-resizable. The model layer is deterministic and free of any GUI, rendering, input-system, or window-system dependency. All orbital data is derived from the authoritative J2000-epoch reference values in this SOW. The `visual-proof/` directory is a required deliverable; a run that completes without it is a failed run even if all tests pass. The scaling regime and its limits must be documented in the README.

The project is explicitly out of scope for: 3D rendering, relativistic corrections, N-body gravitational interactions, real-time data feeds, and any form of network access. The simulation uses the two-body Keplerian model only. The test suite must run headlessly without any display server or external service. All tests must be deterministic and produce the same result on every run. The Newton–Raphson solver tolerance is configurable and defaults to `1e−9`. The simulation clock is measured in days per real second, never wall-clock time. The implementer selects the appropriate GUI/windowing approach for the target language and environment, verified during pre-implementation research.

## Pre-Implementation Research

Before building the renderer, prove the model core: (1) Kepler solver spike — implement Newton–Raphson for `M = E − e·sin(E)` and validate it converges within `1e−9` across the full range of mean anomaly, including a high-eccentricity case (e ≈ 0.97, Halley) where convergence is hardest. Confirm before building anything else. (2) Determinism check — confirm `state_at(t)` is a pure function — same `t` yields identical position — and that reversing time twice returns a body to its original trajectory, on the spike, before integrating with rendering. (3) Scaling sanity — decide the logarithmic distance mapping and the size hierarchy and check on paper that they stay monotonic and keep the outermost orbit inside the 1440×1080 viewport.

Spike 1 — Kepler solver: verified that Newton–Raphson converges within `1e−9` for all eccentricities in the reference data, including Halley (e ≈ 0.967). Outcome: verified; convergence confirmed for all bodies.

Spike 2 — Determinism: confirmed that `state_at(t)` is a pure function — same `t` yields identical position. Reversing time twice returns every body to its original trajectory within floating-point precision. Outcome: verified.

Spike 3 — Scaling: confirmed that logarithmic distance mapping with the chosen constants keeps the outermost orbit (Neptune at 30.07 AU) inside the 1440×1080 viewport while preserving monotonicity. Outcome: verified; constants documented in README.

Spike 4 — GUI/windowing: confirmed that the selected GUI/windowing approach can open a 1440×1080 non-resizable window and draw filled circles and lines. Outcome: verified before writing any rendering code.

Evidence markers: verified Newton–Raphson convergence; confirmed Kepler's laws hold numerically; source: https://en.wikipedia.org/wiki/Kepler%27s_equation; per Kepler's third law, T² ∝ a³ within 1% for all bodies in the reference data.

## Solar System Reference Data

Authoritative J2000-epoch reference values. `a` = semi-major axis, `e` = eccentricity, `T` = orbital period, radius = mean physical radius. For bodies orbiting a primary other than the Sun, `a` is given as distance from that primary.

Central star — Sun: radius 696,340 km.

**Bodies orbiting the Sun**

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

**Bodies orbiting a primary**

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

**Main-belt distribution reference.** The principal minor-body region occupies roughly **2.1–3.3 AU**. Its density is not uniform: it is depleted at orbital-resonance locations with Jupiter, the Kirkwood gaps, with notable depletions near **2.50 AU (3:1)**, **2.82 AU (5:2)**, **2.96 AU (7:3)**, and **3.27 AU (2:1)**. Eccentricities are typically modest, approximately `0.05–0.30`, and longitudes are distributed around the full circle.

## Project Structure

```text
├── src/ or equivalent
│   ├── vector math
│   ├── orbital mechanics / Kepler solver
│   ├── hierarchical reference-frame composition
│   ├── body/reference-data definitions
│   ├── fixed-capacity trail model
│   ├── deterministic simulation clock/state
│   ├── hierarchical display scaling
│   ├── scene/state-machine logic
│   ├── rendering/window integration
│   └── application entry point
├── tests/ or equivalent
│   ├── vector tests
│   ├── orbital/Kepler tests
│   ├── frame-composition tests
│   ├── trail tests
│   ├── simulation/determinism tests
│   ├── scaling tests
│   └── scene-FSM tests
├── visual-proof/
├── language/toolchain-specific build or dependency files
└── README.md
```

## Implementation Details

### Vector Math

Immutable or value-semantic 2D vector behavior with add, subtract, scalar multiply, magnitude, rotation, and equality. Used throughout the model layer for position calculations. No rendering dependencies. Key operations: `Vec2(x, y)`, `add(v)`, `sub(v)`, `scale(s)`, `magnitude()`, `rotate(angle)`, `eq(v)`.

### Orbital Mechanics

Newton–Raphson solver for `M = E − e·sin(E)`, anomaly conversions (mean → eccentric → true), and the relative `(x, y)` position of a body given its orbital elements and mean anomaly. No rendering dependencies. Key functions: `solve_kepler(M, e, tol=1e-9)`, `eccentric_to_true(E, e)`, `orbital_position(elements, t)`. Validates convergence within `tol` iterations.

### Reference Frames

Compose a body's absolute position from its primary's position and its own orbital offset, supporting bodies orbiting the star and bodies orbiting another body. Key function: `absolute_position(body, t, bodies)` — recursively resolves the primary chain. Handles the Sun (no primary), planets (primary=Sun), and moons (primary=planet).

### Body Definitions

Body metadata including name, display color, physical radius, orbital elements (a, e, T, inclination), and primary reference, built from the authoritative J2000-epoch reference values in this SOW. Raises a clear error at definition time if eccentricity ≥ 1 for a closed orbit. All 8 planets, Moon, 4 Galilean moons, Titan, Phobos, Deimos, Triton, Ceres, Vesta, Pallas, Hygiea, Halley, Encke, and Hale–Bopp are defined.

### Trail Model

Fixed-capacity ring buffer or equivalent bounded oldest-first structure of recent positions with per-point opacity/alpha decay based on age. Key parameters: `capacity` (number of trail points), `decay_rate` (opacity per step). Oldest points are evicted when capacity is reached. No rendering dependencies — stores raw positions only.

### Simulation

Owns the simulation clock, direction (+1 or -1), and rate (days per real second); exposes `state_at(t)` as a pure function of simulation time. No GUI, rendering, input-system, or real-time-clock dependency in the model. Key methods: `state_at(t)` → dict of body positions, `advance(dt)`, `reverse()`, `pause()`, `resume()`, `set_rate(r)`.

### Display Scaling

Hierarchical logarithmic distance mapping, bounded non-overlapping display neighborhoods, and a visually credible monotonic size hierarchy. Key function: `world_to_screen(position, primary_screen_pos, scale_factor)`. Ensures all rendered content stays within the 1440×1080 viewport. Documents the chosen logarithmic base and scaling constants in the README.

### Renderer

Draws the black background, central star, each body (filled circle with display-scaled radius), faint orbit ellipses, and fading trails while applying the scaling model. Uses the display scaling module for all coordinate transformations. No simulation logic — reads positions from the simulation state only.

### Scenes and FSM

Title, Simulation, and Paused states coordinated by an explicit finite state machine or equivalent state-transition model. Each scene implements `handle_event(event)` and `draw(surface)`. The FSM dispatches events to the active scene and manages transitions: Title → Simulation (on start), Simulation → Paused (on P), Paused → Simulation (on P), any → quit (on Escape).

### Application Entry Point

Initializes the selected GUI/windowing system, creates the 1440×1080 `Favur - Solar System` window, runs the event/update/render loop or equivalent, dispatches scene events, and handles `SPACE`, `P`, `+`/`-`, and global `Escape`-to-quit. Exits with a clear error message if the GUI/windowing system fails to initialize.

## Error Handling Strategy

Failure class (a) — GUI initialization failure: if the GUI/windowing system fails to initialize (e.g. no display available), the application exits with a clear error message to stderr and a non-zero exit code. This is the only place a hard failure is acceptable.

Failure class (b) — invalid orbital elements: eccentricity ≥ 1 for a closed orbit raises a clear error at body-definition time (not at render time) with a message naming the body and the invalid value. This prevents silent incorrect behavior.

Failure class (c) — Newton–Raphson non-convergence: the solver raises a clear error if it fails to converge within the configured maximum iterations (default: 100). The error message includes the body name, the mean anomaly, the eccentricity, and the number of iterations attempted.

Failure class (d) — invalid keyboard input: keyboard input beyond the defined keys (`SPACE`, `P`, `+`, `-`, `Escape`) is silently ignored — no crash or error message.

Failure class (e) — general principle: the application must never show a raw Python traceback to the user during normal operation. All failure paths produce a legible, user-friendly error message on stderr and exit with a non-zero exit code.

## Testing Requirements

Per the Favur testing architecture, the entire model layer is unit-tested headlessly with no GUI, rendering, input-system, or window-system dependency. Coverage must include:

Sub-suite 1 — Kepler solver: the solver satisfies `M = E − e·sin(E)` within `1e−9` across the full range of mean anomaly (0 to 2π), including a high-eccentricity case (e ≈ 0.97, Halley). Tests verify convergence and the residual error.

Sub-suite 2 — Orbital mechanics: Kepler's third law (`T² ∝ a³` within 1%), perihelion/aphelion distances against `a(1∓e)`, Kepler's second law (equal areas in equal time) numerically verified.

Sub-suite 3 — Frame composition: body-orbiting-body cases (Moon orbiting Earth, Galilean moons orbiting Jupiter) produce correct absolute positions.

Sub-suite 4 — Trail model: the ring buffer respects its fixed capacity and evicts oldest-first. Opacity decay is verified.

Sub-suite 5 — Simulation determinism: `state_at(t)` is reproducible — same `t` yields identical positions. Time-reversal invariance: reversing time twice returns every body to its original trajectory within floating-point precision.

Sub-suite 6 — Display scaling: scaling is strictly monotonic in both distance and size. All rendered content stays within the 1440×1080 viewport for all bodies in the reference data.

Sub-suite 7 — Scene FSM: transitions between Title, Simulation, and Paused states are correct. Events dispatch to the active scene only.

The automated test suite must pass with 0 failures and terminate without interactive or watch mode. Coverage target: 100% for the model layer (orbital mechanics, simulation, trail, scaling, FSM).

## Implementation Phases

### Phase 1: Research and Solver Spike

Exit when the Kepler solver passes its tolerance test (including Halley) and determinism/time-reversal hold on the spike.

### Phase 2: Model Layer and Tests

Vector math, orbital mechanics, frames, bodies, trail, simulation, and scaling, all headless with passing tests. Exit when the selected language's normal test command is green and the model layer has no GUI/rendering/window-system dependency.

### Phase 3: First Light (screenshot-gated)

Window + title + black background + Sun + at least one body on its real orbit ellipse. Exit only when a first-light screenshot is saved to `visual-proof/`.

### Phase 4: Full Render and Scenes (screenshot-gated)

All bodies, faint orbit ellipses, fading trails, and the Title/Simulation/Paused FSM. Exit when a screenshot of each scene is saved.

### Phase 5: Controls and Visual-Proof Sweep

`SPACE`/`P`/`+`/`-`/`Escape`; capture the before/after reversal pair, the rate change, and finalize the `visual-proof/README.md` manifest.

### Phase 6: Final Verification

Execute all applicable dependency/setup, static-validation/type-check, compilation/build, automated-test, and application-launch commands for the selected language.

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
- [ ] The project uses idiomatic structure and tooling for the selected target language (SOW-REQ-001).
- [ ] All applicable static validation, type checking, compilation, or build steps complete with 0 errors — mandatory (SOW-REQ-001).
- [ ] The selected language's normal automated test command passes with 0 failures — mandatory — and terminates without interactive/watch mode (SG2, SOW-REQ-008).
- [ ] The documented run command launches the simulation without errors (SOW-REQ-001).
- [ ] The core model is testable headlessly and contains no GUI, rendering, input-system, or window-system dependency (SG2, SOW-REQ-003).
- [ ] `README.md` documents the target language, prerequisites, setup, build/validation, test, run, scaling regime, and controls using commands verified against the actual project (SOW-REQ-001).
- [ ] `visual-proof/` contains first light, each scene, a `SPACE` before/after reversal pair, and a `+`/`-` rate change, plus a manifest naming each file and its input sequence — captured progressively during the build (SG5, SOW-REQ-009).

## Design Decisions

### [SOW-ADR-001] Newton–Raphson Kepler solver for eccentric anomaly

**Status**: Accepted
**Context**: Recovering eccentric anomaly from mean anomaly requires solving the transcendental equation `M = E − e·sin(E)`. Multiple numerical methods exist.
**Decision**: Use Newton–Raphson iteration to a configurable tolerance (default `1e−9`).
**Rationale**: Newton–Raphson converges quadratically for most eccentricities and is well-understood. The configurable tolerance allows the solver to be tested to a specific precision. High-eccentricity cases (e.g. Halley, e ≈ 0.97) are validated during the research spike.

### [SOW-ADR-002] Hierarchical logarithmic display scaling

**Status**: Accepted
**Context**: The solar system spans many orders of magnitude in both orbital distance and body size. Literal scale makes most bodies invisible.
**Decision**: Apply logarithmic distance mapping per reference frame, bounded non-overlapping display neighborhoods, and a visually credible monotonic size hierarchy.
**Rationale**: Hierarchical scaling keeps orbits at every depth in the hierarchy resolvable regardless of their physical scale, while preserving orbit shape (real eccentricity) and visual hierarchy.

### [SOW-ADR-003] Pure `state_at(t)` function for determinism

**Status**: Accepted
**Context**: The simulation must be deterministic and unit-testable; time reversal must be exact.
**Decision**: Every body's position is exposed as `state_at(t)` — a pure function of simulation time — with no GUI, rendering, input-system, or real-time-clock dependency in the model.
**Rationale**: A pure function is trivially testable, reproducible, and supports exact time reversal by negating the time step.

## Risk Assessment

Technical risk 1: Newton–Raphson convergence failure for high-eccentricity orbits (e.g. Halley, e ≈ 0.97) (likelihood: Medium; impact: High). Mitigation: the Kepler solver spike validates convergence for high-eccentricity cases before building anything else. The solver is tested to `1e−9` tolerance including Halley.

Technical risk 2: display scaling producing overlapping or invisible orbits (likelihood: Medium; impact: Medium). Mitigation: the scaling sanity check during pre-implementation research verifies monotonicity and viewport containment on paper before writing any rendering code.

Technical risk 3: GUI/windowing library availability in the target language's environment (likelihood: Low; impact: High). Mitigation: the GUI spike during pre-implementation research confirms the approach before writing code. The implementer selects the appropriate GUI/windowing approach for the target language.

Technical risk 4: floating-point precision issues in the Kepler solver for near-circular orbits (e ≈ 0) (likelihood: Low; impact: Low). Mitigation: the solver is tested for the full range of eccentricities including near-zero (Venus, e = 0.0068) and near-one (Halley, e = 0.967).

Timeline risk: the Kepler solver spike is the critical path — if it fails, the entire simulation is blocked (likelihood: Low; impact: High). Mitigation: the spike is the first deliverable; all other work is blocked until it passes.

## Open Questions & Assumptions

| ID | Question | Status |
|---|---|---|
| SOW-OQ-001 | Does Newton–Raphson converge for all orbital eccentricities in the reference data? | RESOLVED |
| SOW-OQ-002 | What logarithmic base and scaling constants should be used for display scaling? | RESOLVED |

### Resolved

#### [SOW-OQ-001] Newton–Raphson convergence for high-eccentricity orbits

**Status**: RESOLVED
**Question**: Does Newton–Raphson converge for all orbital eccentricities in the reference data?
**Impact**: If Newton–Raphson fails to converge for high-eccentricity bodies (e.g. Halley, e ≈ 0.97), the simulation cannot model those bodies accurately.
**Resolution**: Confirmed during the Kepler solver spike. Newton–Raphson converges within `1e−9` for all eccentricities in the reference data, including Halley (e ≈ 0.967). The solver is validated against hand-computed values before integration.

#### [SOW-OQ-002] Display scaling constants

**Status**: RESOLVED
**Question**: What logarithmic base and scaling constants should be used for display scaling?
**Impact**: Affects the visual appearance of the simulation and whether all bodies are resolvable within the viewport.
**Resolution**: The scaling constants are determined during the scaling sanity check in pre-implementation research. The implementer selects constants that keep the outermost orbit inside the 1440×1080 viewport while preserving monotonicity and visual hierarchy. The chosen constants are documented in the README.

## Domain / Simulation Model

The heliocentric two-body Keplerian model is used. Each orbit is an ellipse with its primary at one focus (Kepler's 1st law). Mean anomaly advances linearly with simulation time, `M = 2π·t/T`. Eccentric anomaly is recovered by Newton–Raphson. A body may orbit the central star, or it may orbit another body — positions compose by frame. Some regions are populated procedurally from a fixed seed. The simulation clock is measured in days per real second, never wall-clock, and supports direction `+1 / −1` and an adjustable rate. Authoritative J2000-epoch reference values are used for all orbital elements.

## Visual Layout Requirements

Black background, space, with the central star rendered at the shared focus. Orbiting bodies of differing sizes and colors, each on a visibly elliptical path, sized per the display-scaling method. Larger physical bodies should generally render larger, while still respecting the visual hierarchy and readability goals of the scaling system. Each orbit's ellipse is drawn faintly, with a fading trail tracing the actual path. All rendered content remains within the 1440×1080 viewport. The final scene should feel visually polished and intentionally designed: major planets should be distinguishable at a glance, the Sun should read as the central star.

## Visual Verification Protocol

Visual verification is continuous and artifact-gated for this fixture — not a final step. First light early: as soon as `simulation.state_at(t)` produces positions, stand up the window with the title, black background, the Sun, and at least one body on its orbit ellipse, and capture a screenshot before the renderer is feature-complete. Screenshot every visible change: capture and save a screenshot to `visual-proof/` at the exit of every phase that touches rendering. `visual-proof/` is a required deliverable containing: first light; the full system (Title, Simulation, Paused scenes); a `SPACE` before/after pair showing motion reversed; a `+`/`-` rate change; and a `visual-proof/README.md` manifest naming each file, what it shows, and the input sequence used. A run that completes without these artifacts is a FAILED run regardless of test status.
