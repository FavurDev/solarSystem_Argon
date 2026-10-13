# Favur - Solar System (`solar-system`)

Interactive 2D Keplerian solar system simulation with a pure-Python headless orbital mechanics engine (`vector.py`, `kepler.py`, `trail.py`, `bodies.py`, `frames.py`, `simulation.py`, `scaling.py`, `scenes.py`) and a Pygame 2D rendering and HUD overlay layer (`renderer.py`, `hud.py`, `main.py`).

---

## 1. Target Language & Runtime Prerequisites

| Parameter | Value | Type | Usage |
| :--- | :--- | :--- | :--- |
| `TARGET_LANGUAGE` | `"Python 3.11+"` | `string` | Minimum supported Python language version (`Python 3.13` verified; `pyproject.toml` constraint `>=3.12,<4.0`) |
| `RENDERING_ENGINE` | `"Pygame >= 2.5.0"` | `string` | 2D software/hardware display surface and event loop (`pygame >=2.5.0,<3.0.0`, `Pygame 2.6.1` verified) |
| `BUILD_SYSTEM` | `"Poetry"` | `string` | Dependency management, virtual environment isolation, and CLI entry-point runner (`poetry-core >=2.0.0,<3.0.0`) |
| `WINDOW_TITLE` | `"Favur - Solar System"` | `string` | Exact OS window caption required by visual-proof verification |
| `VIEWPORT_WIDTH_PX` | `1440` | `number` | Default viewport width in pixels (`16:9` / `4:3` high-DPI desktop layout) |
| `VIEWPORT_HEIGHT_PX` | `1080` | `number` | Default viewport height in pixels |
| `SUN_CENTER_PX` | `(720, 540)` | `tuple[int, int]` | Default screen-space pixel coordinates of the active reference-frame origin |
| `TARGET_FPS` | `60` | `number` | Target frame rate in frames per second (`dt_wall_s = 1.0 / 60.0`) |

---

## 2. Setup, Lint, Typecheck, Test, Build, and Run Commands

Run all commands from the repository root (`argon-solarSystem/`):

```bash
# 1. Install dependencies and package entry point
poetry install

# 2. Run Ruff linter across all source and test files
poetry run ruff check .

# 3. Run strict Mypy static type checking across src and tests
poetry run mypy src tests

# 4. Execute the headless pytest unit and integration test suite
poetry run pytest

# 5. Build sdist and wheel distribution artifacts in dist/
poetry build

# 6. Launch the interactive 1440x1080 Pygame Solar System simulation
poetry run solar-system
```

Alternative module invocation:

```bash
poetry run python -m solar_system.main
```

---

## 3. Architecture Summary

The package (`src/solar_system/`) enforces a strict separation between the headless mathematical model and the Pygame presentation layer:

1. **Headless Model Layer (Zero Pygame Dependency)**:
   - `vector.py`: Immutable 3D Cartesian vector `Vec3(x, y, z)` (`@dataclass(frozen=True, slots=True)`) and active Euler rotations `rotate_z`, `rotate_x`.
   - `kepler.py`: Immutable `OrbitalElements`, exact $2\pi$-modular mean anomaly reduction, safeguarded Newton-Raphson + bisection Kepler equation solver (`MAX_ITER = 32`, `TOL = 1e-12`), and perifocal-to-ecliptic 3D transformation ($r = a(1 - e\cos E)$).
   - `bodies.py`: Immutable J2000.0 (`JD 2451545.0`) catalog containing the Sun (`#FDB813`), 8 planets (`Mercury`, `Venus`, `Earth`, `Mars`, `Jupiter`, `Saturn`, `Uranus`, `Neptune`), 5 dwarf planets (`Pluto`, `Ceres`, `Eris`, `Haumea`, `Makemake`), 12 major moons (`Moon`, `Phobos`, `Deimos`, `Io`, `Europa`, `Ganymede`, `Callisto`, `Titan`, `Enceladus`, `Rhea`, `Iapetus`, `Triton`), 2 periodic comets (`Halley's Comet`, `Comet Encke`), and a deterministic (`seed = 20260413`) 360-asteroid main belt (`[2.06, 3.28] AU`) with sinusoidal Kirkwood resonance notches at `4:1` (`2.065 AU`), `3:1` (`2.502 AU`), `5:2` (`2.825 AU`), `7:3` (`2.958 AU`), and `2:1` (`3.278 AU`).
   - `frames.py`: `ReferenceFrame` (`HELIOCENTRIC`, `EARTH_CENTERED`, `JUPITER_CENTERED`, `SATURN_CENTERED`, `PLUTO_CENTERED`) and parent-chain 3D coordinate folding.
   - `trail.py`: Immutable `OrbitPoint(x_au, y_au, z_au, epoch_days)` and bounded FIFO ring buffer `TrailBuffer(max_points = 180)`.
   - `simulation.py`: `SimulationState` authoritative clock (`sim_days` in days from J2000.0), time-direction state machine (`time_direction` in `{-1, +1}`), 9-step warp ladder, reference-frame selector, and scene preset controller.
   - `scaling.py`: Immutable `DisplayScaleConfig` and pure-Python hierarchical base-10 logarithmic coordinate and radius transformations.
   - `scenes.py`: Immutable `ScenePreset` definitions for scenes `1` through `5`.
2. **Presentation Layer (Pygame 2D)**:
   - `renderer.py`: Multi-layer Pygame painter's algorithm renderer (starfield, Kirkwood asteroid belt, 180-vertex focus-preserving orbit polylines, fading trajectory trails, body discs with specular/ring/coma overlays, collision-avoiding screen-space labels).
   - `hud.py`: Telemetry panel (J2000 UTC date/time, signed warp rate, `FORWARD`/`REVERSE`/`PAUSED` status badge, active reference frame, active scene preset), logarithmic AU scale bar, interactive keybindings legend, and initial launch banner (`PRESS ENTER TO START SIMULATION`).
   - `main.py`: CLI entry point (`solar_system.main:main`) and 60 FPS event loop.

---

## 4. Hierarchical Base-10 Logarithmic Scaling Equations & Constants

Real solar-system distances span more than six orders of magnitude—from Mars's inner moon Phobos at `a = 0.0000627 AU` (`9,376 km`) to Comet Halley's aphelion at `Q = 35.08 AU`, Eris's aphelion at `Q = 97.46 AU`, and the outer Oort/Kuiper viewport boundary at `375.0 AU`. Physical body radii similarly span from `R_Deimos = 6.2 km` to `R_Sun = 696,340 km`.

`src/solar_system/scaling.py` (`DisplayScaleConfig`) implements a two-level hierarchical base-10 logarithmic coordinate transform and logarithmic radius mapping so all bodies remain simultaneously visible and non-overlapping inside the `1440x1080` viewport (`sun_center = (720, 540)`).

### 4.1 Level 1: Heliocentric Distance Mapping (`[0.30, 375.0] AU` -> `[52.0, 500.0] px`)

For any primary body (planet, dwarf planet, comet, or asteroid) at heliocentric ecliptic distance `r = sqrt(x_au^2 + y_au^2)` (in AU), the normalized logarithmic coordinate `u(r) in [0.0, 1.0]` and screen-space radial distance `r_px(r)` (in pixels at `zoom = 1.0`) are defined by:

```text
u(r)    = clamp((log10(max(r, 0.30)) - log10(0.30)) / (log10(375.0) - log10(0.30)), 0.0, 1.0)
r_px(r) = 52.0 + 448.0 * u(r)
```

Screen-space pixel coordinates `(X_px, Y_px)` preserve the exact heliocentric direction cosine `(cos_theta, sin_theta) = (x_au / r, y_au / r)` with screen `+Y` pointing downward:

```text
X_px = X_center + zoom * r_px(r) * (x_au / r)
Y_px = Y_center - zoom * r_px(r) * (y_au / r)
```

| Constant | Value | Type | Usage |
| :--- | :--- | :--- | :--- |
| `VIEWPORT_WIDTH` | `1440` | `number` | Viewport width in pixels |
| `VIEWPORT_HEIGHT` | `1080` | `number` | Viewport height in pixels |
| `SUN_CENTER` | `(720, 540)` | `tuple[int, int]` | Default viewport origin `sun_center = (720, 540)` in pixels |
| `MIN_AU` | `0.30` | `number` | Inner heliocentric logarithmic clamp in AU (inside Mercury perihelion `0.3075 AU`) |
| `MAX_AU` | `375.0` | `number` | Outer heliocentric logarithmic clamp in AU |
| `MIN_PX` | `52.0` | `number` | Inner screen-space radius in pixels at `r = 0.30 AU` |
| `MAX_PX` | `500.0` | `number` | Outer screen-space radius in pixels at `r = 375.0 AU` |
| `SPAN_PX` | `448.0` | `number` | Heliocentric radial pixel span (`500.0 - 52.0`) |

### 4.2 Level 2: Moon Neighborhood Local Logarithmic Mapping (`[0.00006, 0.04] AU` -> `[16.0, 28.0] px`)

Natural satellites orbit at `1e-5` to `4e-2 AU` from their parent planet (`6.27e-5 AU` for Phobos to `2.38e-2 AU` for Iapetus). To prevent moons from collapsing into their parent planet's rendered disc, each moon's planetocentric offset `(dx_au, dy_au) = (x_moon - x_parent, y_moon - y_parent)` with planar magnitude `d = sqrt(dx_au^2 + dy_au^2)` is mapped onto a local logarithmic annulus `[16.0, 28.0] px` around the parent planet's projected screen coordinates `(X_parent, Y_parent)`:

```text
u_moon(d)    = clamp((log10(max(d, 0.00006)) - log10(0.00006)) / (log10(0.04) - log10(0.00006)), 0.0, 1.0)
r_moon_px(d) = 16.0 + 12.0 * u_moon(d)
X_moon_px    = X_parent + zoom * r_moon_px(d) * (dx_au / d)
Y_moon_px    = Y_parent - zoom * r_moon_px(d) * (dy_au / d)
```

| Constant | Value | Type | Usage |
| :--- | :--- | :--- | :--- |
| `MOON_MIN_AU` | `0.00006` | `number` | Inner planetocentric distance clamp in AU (`6.0e-5 AU`, inside Phobos `6.27e-5 AU`) |
| `MOON_MAX_AU` | `0.04` | `number` | Outer planetocentric distance clamp in AU (`4.0e-2 AU`, outside Iapetus `2.38e-2 AU`) |
| `MOON_MIN_PX` | `16.0` | `number` | Inner local offset radius in pixels around parent planet screen coordinates |
| `MOON_MAX_PX` | `28.0` | `number` | Outer local offset radius in pixels around parent planet screen coordinates |
| `MOON_NEIGHBORHOOD_RADII_PX["Earth"]` | `18.0` | `number` | Earth lunar neighborhood outer visual envelope in pixels |
| `MOON_NEIGHBORHOOD_RADII_PX["Mars"]` | `16.0` | `number` | Mars satellite neighborhood outer visual envelope in pixels |
| `MOON_NEIGHBORHOOD_RADII_PX["Jupiter"]` | `28.0` | `number` | Jupiter Galilean satellite neighborhood outer visual envelope in pixels |
| `MOON_NEIGHBORHOOD_RADII_PX["Saturn"]` | `22.0` | `number` | Saturn satellite neighborhood outer visual envelope in pixels |
| `MOON_NEIGHBORHOOD_RADII_PX["Neptune"]` | `18.0` | `number` | Neptune (Triton) satellite neighborhood outer visual envelope in pixels |

### 4.3 Body Display Radius Mapping

Physical volumetric radius `R_km` is mapped to integer screen pixel radius `r_body_px` via a clamped base-10 logarithmic law anchored at `R_0 = 500.0 km`:

```text
r_body_px = clamp(round(2.5 + 3.2 * log10(max(R_km, 500.0) / 500.0)), 2, 14)
```

Continuous reference curve (`SOW-OQ-002` / `SOW-ADR-004` baseline): `r_px = clamp(1.2 + 2.15 * log10(radius_km), 2.0, 14.0)` (`Sun = 20.0 px` baseline; integer `DisplayScaleConfig` sets `Sun = 18 px` core disc `+ 4 px` corona glow `= 22 px` total outer radius).

| Body Category | Scaling Rule / Constant | Pixel Radius (`px`) |
| :--- | :--- | :--- |
| **Sun** (`R_km = 696340.0`) | Fixed core disc `SUN_RADIUS_PX = 18` + `SUN_GLOW_PX = 4` (`20.0 px` nominal reference) | `18 px` (`+ 4 px` glow = `22 px`) |
| **Gas & Ice Giants** (`Jupiter`, `Saturn`, `Uranus`, `Neptune`) | `r_body_px = clamp(round(2.5 + 3.2 * log10(max(R_km, 500.0) / 500.0)), 2, 14)` | `8 px` – `10 px` (clamped at `<= 14 px`) |
| **Terrestrial & Dwarf Planets** (`Mercury`, `Venus`, `Earth`, `Mars`, `Pluto`, `Ceres`, `Eris`, `Haumea`, `Makemake`) | `r_body_px = clamp(round(2.5 + 3.2 * log10(max(R_km, 500.0) / 500.0)), 2, 14)` | `2 px` – `6 px` |
| **Major Moons & Comets** (`12` moons, `Halley's Comet`, `Comet Encke`) | `r_body_px = clamp(round(2.5 + 3.2 * log10(max(R_km, 500.0) / 500.0)), 2, 14)` | `2 px` – `4 px` |
| **Main-Belt Asteroids** (`360` deterministic belt particles) | Fixed particle size (`ASTEROID_MIN_PX = 1`, `ASTEROID_MAX_PX = 2`) | `1`–`2 px` |

### 4.4 Focus-Preserving 180-Vertex True-Anomaly Orbit Polyline Projection

Because the radial mapping `r -> r_px(r)` is logarithmic rather than affine, an ellipse in `(x_au, y_au)` does not project to a standard screen-space ellipse. Drawing a naive symmetric screen-space bounding-box ellipse would displace the Sun from the focal point and cause high-eccentricity bodies (`Halley's Comet` at `e = 0.96714`, `Comet Encke` at `e = 0.84830`, `Eris` at `e = 0.43607`, `Pluto` at `e = 0.24883`, `Mercury` at `e = 0.20563`) to detach visually from their rendered orbit curves.

Instead, every orbit guide curve is computed by sampling `N = 180` exact true-anomaly vertices (`nu_k = 2*pi*k/180`) around the Keplerian orbit:

```text
nu_k    = 2 * pi * k / 180,    k in {0, 1, ..., 179}
r(nu_k) = a * (1 - e^2) / (1 + e * cos(nu_k))
```

Each sample `(r(nu_k) * cos(nu_k), r(nu_k) * sin(nu_k), 0)` in the perifocal frame is rotated into the 3D J2000 ecliptic frame by `R_z(-Omega) * R_x(-i) * R_z(-omega)`, transformed into the active reference frame, and projected through the exact same logarithmic transformation `world_to_screen` (`[0.30, 375.0] AU` -> `[52.0, 500.0] px` for heliocentric orbits, or `moon_world_to_screen` `[0.00006, 0.04] AU` -> `[16.0, 28.0] px` for satellite orbits). This guarantees that every body lies on its rendered orbit polyline at all times `t` and under both forward (`+1`) and reverse (`-1`) integration.

---

## 5. Keyboard Controls & Interactive Keybindings

All keyboard bindings are processed by the main event loop (`src/solar_system/main.py`) and mutated on `SimulationState` (`src/solar_system/simulation.py`):

| Key(s) | Pygame Key Constant(s) | Action | State Mutation / Behavior |
| :--- | :--- | :--- | :--- |
| `ENTER` / `RETURN` | `K_RETURN`, `K_KP_ENTER` | Start / Resume Simulation | Clears initial launch prompt (`started = True`, `paused = False`) and begins time integration |
| `SPACE` | `K_SPACE` | Toggle Time Direction | Multiplies `time_direction` by `-1` (`+1` `FORWARD` <-> `-1` `REVERSE`) without altering `sim_days` or `speed_index` |
| `P` | `K_p` | Toggle Pause / Resume | Flips `paused` (`True` <-> `False`); preserves `sim_days`, `time_direction`, and `speed_index` |
| `+` / `=` / `KP_PLUS` | `K_PLUS`, `K_EQUALS`, `K_KP_PLUS` | Increase Warp Speed | Increments `speed_index = min(speed_index + 1, 8)` along `SPEED_LADDER_DAYS_PER_SEC` |
| `-` / `KP_MINUS` | `K_MINUS`, `K_KP_MINUS` | Decrease Warp Speed | Decrements `speed_index = max(speed_index - 1, 0)` along `SPEED_LADDER_DAYS_PER_SEC` |
| `R` | `K_r` | Reset Epoch to J2000.0 | Resets `sim_days = 0.0` (`2000-01-01 12:00:00 UTC`), sets `time_direction = +1`, and clears all `TrailBuffer` histories |
| `TAB` / `SHIFT+TAB` | `K_TAB` (`KMOD_SHIFT`) | Cycle Reference Frame | Cycles `active_frame` forward (`TAB`) or backward (`SHIFT+TAB`) through `HELIOCENTRIC` -> `EARTH_CENTERED` -> `JUPITER_CENTERED` -> `SATURN_CENTERED` -> `PLUTO_CENTERED` and clears trails |
| `1` | `K_1`, `K_KP1` | Scene Preset 1: Full Solar System | Sets `active_preset_id = 1`, `active_frame = HELIOCENTRIC`, `speed_index = 4` (`10.0 d/s`), `zoom = 1.0`, `pan_px = (0.0, 0.0)` |
| `2` | `K_2`, `K_KP2` | Scene Preset 2: Inner Terrestrial & Moon | Sets `active_preset_id = 2`, `active_frame = HELIOCENTRIC`, `speed_index = 2` (`1.0 d/s`), `zoom = 2.35`, `pan_px = (0.0, 0.0)` |
| `3` | `K_3`, `K_KP3` | Scene Preset 3: Kirkwood Asteroid Belt | Sets `active_preset_id = 3`, `active_frame = HELIOCENTRIC`, `speed_index = 4` (`10.0 d/s`), `zoom = 1.65`, `pan_px = (0.0, 0.0)` |
| `4` | `K_4`, `K_KP4` | Scene Preset 4: Gas Giant Moons (Jupiter & Saturn) | Sets `active_preset_id = 4`, `active_frame = JUPITER_CENTERED`, `speed_index = 1` (`0.25 d/s`), `zoom = 1.85`, `pan_px = (0.0, 0.0)` |
| `5` | `K_5`, `K_KP5` | Scene Preset 5: Outer Kuiper Belt, Dwarf Planets & Comets | Sets `active_preset_id = 5`, `active_frame = HELIOCENTRIC`, `speed_index = 6` (`100.0 d/s`), `zoom = 0.92`, `pan_px = (0.0, 0.0)` |
| `[` / `]` | `K_LEFTBRACKET`, `K_RIGHTBRACKET` | Zoom Out / Zoom In | Multiplies camera `zoom` by `1 / 1.15` (`[`) or `1.15` (`]`), clamped to `[0.5, 4.0]` |
| `ESC` | `K_ESCAPE` | Quit Application | Terminates the Pygame event loop cleanly and exits with code `0` |

### Warp Speed Ladder (`SPEED_LADDER_DAYS_PER_SEC`)

| `speed_index` | Rate (`days / sec`) | Effective Advance per Frame (`60 FPS`) | Typical Use Case |
| :---: | :---: | :---: | :--- |
| `0` | `0.05` | `0.000833 days` (`1.2 min`) | Close lunar & Phobos/Deimos motion |
| `1` | `0.25` | `0.004167 days` (`6.0 min`) | Galilean & Saturnian moon systems (Preset 4) |
| `2` | `1.0` | `0.016667 days` (`24.0 min`) | Inner terrestrial planets (Preset 2) |
| `3` | `5.0` | `0.083333 days` (`2.0 hr`) | Inner solar system & Comet Encke |
| `4` | `10.0` (default) | `0.166667 days` (`4.0 hr`) | Full solar system overview & Kirkwood belt (Presets 1 & 3) |
| `5` | `30.0` | `0.500000 days` (`12.0 hr`) | Mars, Jupiter, and Saturn orbital revolutions |
| `6` | `100.0` | `1.666667 days` (`40.0 hr`) | Outer planets, Kuiper belt & Halley's Comet (Preset 5) |
| `7` | `365.25` | `6.087500 days` (`1 J2000 yr / s`) | Multi-decade outer solar system dynamics |
| `8` | `1826.25` | `30.437500 days` (`5 J2000 yr / s`) | Pluto (`248 yr`), Haumea (`284 yr`), Makemake (`306 yr`), Eris (`559 yr`) orbits |

---

## 6. Visual-Proof Screenshots & Manifest Reference

Progressive visual verification captures 7 deterministic `1440x1080` screenshots under `visual-proof/` and documents them in `visual-proof/README.md`:

| Stage | Artifact Path | Verified Feature |
| :---: | :--- | :--- |
| `01` | `visual-proof/01_first_light.png` | Initial `1440x1080` viewport at J2000.0 (`2000-01-01 12:00 UTC`), Sun at `(720, 540)`, 8 planets, 5 dwarf planets, HUD telemetry, and `PRESS ENTER TO START SIMULATION` prompt |
| `02` | `visual-proof/02_orbital_motion.png` | Active `FORWARD` (`+1`) orbital propagation after pressing `ENTER`, showing curved trajectory trails and updated J2000 epoch |
| `03` | `visual-proof/03_kirkwood_asteroid_belt.png` | Scene Preset `3` (`1.65x` zoom) highlighting the 360-asteroid main belt (`[2.06, 3.28] AU`) and Kirkwood resonance gaps (`3:1`, `5:2`, `7:3`, `2:1`) |
| `04` | `visual-proof/04_moons_and_comets.png` | Local logarithmic satellite neighborhoods (`Moon`, `Phobos`, `Deimos`, `Io`, `Europa`, `Ganymede`, `Callisto`, `Titan`, `Enceladus`, `Rhea`, `Iapetus`, `Triton`) and eccentric comet orbits (`Halley's Comet`, `Comet Encke`) |
| `05` | `visual-proof/05_reference_frame_shift.png` | Reference frame cycling via `TAB` (`JUPITER_CENTERED` / `SATURN_CENTERED` / `EARTH_CENTERED`) with re-centered origin and cleared trails |
| `06` | `visual-proof/06_time_reversal.png` | Time-direction reversal via `SPACE` (`REVERSE`, `time_direction = -1`) retracing Keplerian orbits backward in time |
| `07` | `visual-proof/07_rate_change.png` | Warp rate adjustment via `+`/`-` (`365.25 d/s` / `1826.25 d/s`) and `P` pause/resume state |

See [`visual-proof/README.md`](visual-proof/README.md) for the complete stage-by-stage verification manifest, capture timestamps, and multimodal vision audit log.
