"""Immutable J2000 celestial body catalog and Kirkwood gap asteroid belt generator.

Provides the pure-Python data structures ``BodyCategory``, ``VisualStyle``,
``CelestialBody`` (aliased as ``Body``), and ``KirkwoodGap``, along with the
25-body J2000 catalog builder ``build_named_bodies()``, the resonant Kirkwood
gap predicate ``is_in_kirkwood_gap()``, the seeded deterministic asteroid belt
generator ``generate_asteroid_belt()``, and the combined catalog builder
``build_catalog()``.
"""

# CHANGELOG:
# - Sprint 1: Implemented J2000 celestial body catalog and Kirkwood gap asteroid belt generator.

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final, Literal

from solar_system.kepler import J2000_JD, OrbitalElements

type BodyCategory = Literal["star", "planet", "moon", "dwarf", "asteroid", "comet"]

J2000_EPOCH_JD: Final[float] = J2000_JD
JUPITER_PERIOD_DAYS: Final[float] = 4332.589
AU_IN_KM: Final[float] = 149597870.7
EARTH_SIDEREAL_YEAR_DAYS: Final[float] = 365.256363004


@dataclass(frozen=True, slots=True)
class VisualStyle:
    """Pure-Python visual rendering metadata for a celestial body.

    Attributes:
        color_rgb: Primary body fill RGB color ``(r, g, b)`` with channels in ``0..255``.
        radius_px: Base screen rendering radius in pixels.
        trail_color_rgb: Orbit trajectory line and fading trail RGB color ``(r, g, b)``.
        has_rings: Flag indicating whether the body has a planetary ring system.
        ring_inner_mult: Inner ring radius multiplier relative to body radius.
        ring_outer_mult: Outer ring radius multiplier relative to body radius.
    """

    color_rgb: tuple[int, int, int]
    radius_px: int
    trail_color_rgb: tuple[int, int, int]
    has_rings: bool = False
    ring_inner_mult: float = 0.0
    ring_outer_mult: float = 0.0

    @property
    def ring_inner_Mult(self) -> float:
        """Return ``ring_inner_mult`` for specification naming compatibility.

        Returns:
            Inner ring radius multiplier relative to the body radius.
        """
        return self.ring_inner_mult


@dataclass(frozen=True, slots=True)
class CelestialBody:
    """Immutable J2000 catalog record for a star, planet, moon, dwarf, asteroid, or comet.

    Attributes:
        name: Unique canonical identifier (e.g. ``"Sun"``, ``"Earth"``, ``"1P/Halley"``).
        category: Astronomical classification category.
        parent_name: Central gravitational primary name (``None`` only for ``"Sun"``).
        elements: J2000 Keplerian ``OrbitalElements`` (``None`` only for ``"Sun"``).
        mass_kg: Body mass in kilograms.
        radius_km: Mean volumetric radius in kilometers.
        style: Pure-Python ``VisualStyle`` rendering metadata.
        description: Human-readable summary string for the HUD inspector.
    """

    name: str
    category: BodyCategory
    parent_name: str | None
    elements: OrbitalElements | None
    mass_kg: float
    radius_km: float
    style: VisualStyle
    description: str = ""


Body = CelestialBody


@dataclass(frozen=True, slots=True)
class KirkwoodGap:
    """Mean-motion orbital resonance exclusion zone in the main asteroid belt.

    Attributes:
        label: Resonance ratio label (e.g. ``"4:1"``, ``"3:1"``, ``"5:2"``, ``"7:3"``, ``"2:1"``).
        ratio_num: Asteroid orbital frequency numerator ``p``.
        ratio_den: Jupiter orbital frequency denominator ``q``.
        center_au: Resonance center semi-major axis in Astronomical Units.
        half_width_au: Exclusion half-width ``delta_a`` in Astronomical Units.
    """

    label: str
    ratio_num: int
    ratio_den: int
    center_au: float
    half_width_au: float

    @property
    def resonance(self) -> str:
        """Return the mean-motion resonance label string.

        Returns:
            Resonance ratio label such as ``"3:1"``.
        """
        return self.label


KIRKWOOD_GAPS: Final[tuple[KirkwoodGap, ...]] = (
    KirkwoodGap(label="4:1", ratio_num=4, ratio_den=1, center_au=2.065, half_width_au=0.025),
    KirkwoodGap(label="3:1", ratio_num=3, ratio_den=1, center_au=2.502, half_width_au=0.035),
    KirkwoodGap(label="5:2", ratio_num=5, ratio_den=2, center_au=2.825, half_width_au=0.030),
    KirkwoodGap(label="7:3", ratio_num=7, ratio_den=3, center_au=2.958, half_width_au=0.022),
    KirkwoodGap(label="2:1", ratio_num=2, ratio_den=1, center_au=3.278, half_width_au=0.040),
)


def _build_star_and_planets() -> tuple[CelestialBody, ...]:
    """Construct the Sun and the 8 major J2000 planets.

    Returns:
        9-element tuple containing the Sun followed by Mercury through Neptune.
    """
    return (
        CelestialBody(
            name="Sun",
            category="star",
            parent_name=None,
            elements=None,
            mass_kg=1.9885e30,
            radius_km=696340.0,
            style=VisualStyle(
                color_rgb=(255, 220, 80),
                radius_px=14,
                trail_color_rgb=(255, 200, 60),
            ),
            description="G2V main-sequence star at the center of the Solar System.",
        ),
        CelestialBody(
            name="Mercury",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=0.38709893,
                eccentricity=0.20563069,
                inclination_deg=7.00487,
                lon_ascending_node_deg=48.33167,
                arg_periapsis_deg=29.12478,
                mean_anomaly_epoch_deg=174.79439,
                orbital_period_days=87.9691,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=3.3011e23,
            radius_km=2439.7,
            style=VisualStyle(
                color_rgb=(169, 169, 169),
                radius_px=4,
                trail_color_rgb=(140, 140, 140),
            ),
            description="Innermost terrestrial planet with the highest planetary orbital eccentricity.",
        ),
        CelestialBody(
            name="Venus",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=0.72333199,
                eccentricity=0.00677323,
                inclination_deg=3.39471,
                lon_ascending_node_deg=76.68069,
                arg_periapsis_deg=54.85229,
                mean_anomaly_epoch_deg=50.44675,
                orbital_period_days=224.701,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=4.8675e24,
            radius_km=6051.8,
            style=VisualStyle(
                color_rgb=(230, 195, 130),
                radius_px=6,
                trail_color_rgb=(200, 165, 105),
            ),
            description="Dense CO2-shrouded terrestrial planet with near-circular orbit.",
        ),
        CelestialBody(
            name="Earth",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=1.00000011,
                eccentricity=0.01671022,
                inclination_deg=0.00005,
                lon_ascending_node_deg=-11.26064,
                arg_periapsis_deg=114.20783,
                mean_anomaly_epoch_deg=357.51716,
                orbital_period_days=365.25636,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=5.97237e24,
            radius_km=6371.0,
            style=VisualStyle(
                color_rgb=(70, 140, 255),
                radius_px=6,
                trail_color_rgb=(60, 120, 220),
            ),
            description="Third planet from the Sun; reference plane of the J2000 ecliptic.",
        ),
        CelestialBody(
            name="Mars",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=1.52366231,
                eccentricity=0.09341233,
                inclination_deg=1.85061,
                lon_ascending_node_deg=49.57854,
                arg_periapsis_deg=286.46230,
                mean_anomaly_epoch_deg=19.41248,
                orbital_period_days=686.980,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=6.4171e23,
            radius_km=3389.5,
            style=VisualStyle(
                color_rgb=(220, 95, 60),
                radius_px=5,
                trail_color_rgb=(190, 80, 50),
            ),
            description="Fourth planet from the Sun; iron-oxide surface with moons Phobos and Deimos.",
        ),
        CelestialBody(
            name="Jupiter",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=5.20336301,
                eccentricity=0.04839266,
                inclination_deg=1.30530,
                lon_ascending_node_deg=100.55615,
                arg_periapsis_deg=274.19770,
                mean_anomaly_epoch_deg=19.65053,
                orbital_period_days=4332.589,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.8982e27,
            radius_km=69911.0,
            style=VisualStyle(
                color_rgb=(225, 175, 125),
                radius_px=10,
                trail_color_rgb=(195, 150, 105),
            ),
            description="Largest gas giant; drives the resonant Kirkwood gaps in the main asteroid belt.",
        ),
        CelestialBody(
            name="Saturn",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=9.53707032,
                eccentricity=0.05415060,
                inclination_deg=2.48446,
                lon_ascending_node_deg=113.71504,
                arg_periapsis_deg=338.71690,
                mean_anomaly_epoch_deg=317.02074,
                orbital_period_days=10759.22,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=5.6834e26,
            radius_km=58232.0,
            style=VisualStyle(
                color_rgb=(235, 205, 145),
                radius_px=9,
                trail_color_rgb=(205, 175, 120),
                has_rings=True,
                ring_inner_mult=1.5,
                ring_outer_mult=2.3,
            ),
            description="Gas giant with prominent icy ring system and largest moon Titan.",
        ),
        CelestialBody(
            name="Uranus",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=19.19126393,
                eccentricity=0.04716771,
                inclination_deg=0.76986,
                lon_ascending_node_deg=74.22988,
                arg_periapsis_deg=96.73436,
                mean_anomaly_epoch_deg=142.23860,
                orbital_period_days=30685.4,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=8.6810e25,
            radius_km=25362.0,
            style=VisualStyle(
                color_rgb=(135, 215, 230),
                radius_px=7,
                trail_color_rgb=(110, 185, 200),
                has_rings=True,
                ring_inner_mult=1.6,
                ring_outer_mult=2.0,
            ),
            description="Ice giant with extreme axial tilt and faint ring system.",
        ),
        CelestialBody(
            name="Neptune",
            category="planet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=30.06896348,
                eccentricity=0.00858587,
                inclination_deg=1.76917,
                lon_ascending_node_deg=131.72169,
                arg_periapsis_deg=273.24966,
                mean_anomaly_epoch_deg=259.90868,
                orbital_period_days=60189.0,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.02413e26,
            radius_km=24622.0,
            style=VisualStyle(
                color_rgb=(75, 115, 235),
                radius_px=7,
                trail_color_rgb=(65, 100, 205),
            ),
            description="Outermost ice giant orbited by captured retrograde moon Triton.",
        ),
    )


def _build_moons() -> tuple[CelestialBody, ...]:
    """Construct the 9 major J2000 planetary moons with semi-major axes in AU.

    # IMPLEMENTATION DECISION: Divide each moon's semi-major axis in kilometers by
    # AU_IN_KM = 149597870.7 at construction time and encode Triton's retrograde orbit
    # with inclination_deg=156.865 and orbital_period_days=-5.876854.
    # Rationale: OrbitalElements requires semi_major_axis_au in Astronomical Units so
    # keplerian_to_cartesian returns parent-local offsets in AU (DR-003), while negative
    # orbital_period_days with inclination_deg > 90 deg yields L_z < 0 (DR-005).
    # Alternatives: Converting km to AU inside frames.py (would break standalone moon
    # evaluation in keplerian_to_cartesian).

    Returns:
        9-element tuple of moon CelestialBody records.
    """
    return (
        CelestialBody(
            name="Moon",
            category="moon",
            parent_name="Earth",
            elements=OrbitalElements(
                semi_major_axis_au=384399.0 / AU_IN_KM,
                eccentricity=0.0549,
                inclination_deg=5.145,
                lon_ascending_node_deg=125.08,
                arg_periapsis_deg=318.15,
                mean_anomaly_epoch_deg=135.27,
                orbital_period_days=27.321661,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=7.342e22,
            radius_km=1737.4,
            style=VisualStyle(
                color_rgb=(210, 210, 215),
                radius_px=3,
                trail_color_rgb=(175, 175, 185),
            ),
            description="Earth's natural satellite in synchronous rotation.",
        ),
        CelestialBody(
            name="Phobos",
            category="moon",
            parent_name="Mars",
            elements=OrbitalElements(
                semi_major_axis_au=9376.0 / AU_IN_KM,
                eccentricity=0.0151,
                inclination_deg=1.093,
                lon_ascending_node_deg=48.0,
                arg_periapsis_deg=150.0,
                mean_anomaly_epoch_deg=92.0,
                orbital_period_days=0.318910,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.0659e16,
            radius_km=11.267,
            style=VisualStyle(
                color_rgb=(175, 155, 140),
                radius_px=2,
                trail_color_rgb=(145, 130, 115),
            ),
            description="Inner Martian satellite orbiting inside synchronous altitude.",
        ),
        CelestialBody(
            name="Deimos",
            category="moon",
            parent_name="Mars",
            elements=OrbitalElements(
                semi_major_axis_au=23463.2 / AU_IN_KM,
                eccentricity=0.00033,
                inclination_deg=0.93,
                lon_ascending_node_deg=49.0,
                arg_periapsis_deg=290.0,
                mean_anomaly_epoch_deg=196.0,
                orbital_period_days=1.26244,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.4762e15,
            radius_km=6.2,
            style=VisualStyle(
                color_rgb=(165, 150, 135),
                radius_px=2,
                trail_color_rgb=(135, 120, 110),
            ),
            description="Outer Martian satellite in a nearly circular equatorial orbit.",
        ),
        CelestialBody(
            name="Io",
            category="moon",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=421700.0 / AU_IN_KM,
                eccentricity=0.0041,
                inclination_deg=0.036,
                lon_ascending_node_deg=43.977,
                arg_periapsis_deg=84.129,
                mean_anomaly_epoch_deg=342.021,
                orbital_period_days=1.769137,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=8.9319e22,
            radius_km=1821.6,
            style=VisualStyle(
                color_rgb=(245, 220, 95),
                radius_px=3,
                trail_color_rgb=(210, 190, 80),
            ),
            description="Innermost Galilean moon; tidally heated volcanic world.",
        ),
        CelestialBody(
            name="Europa",
            category="moon",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=671034.0 / AU_IN_KM,
                eccentricity=0.0094,
                inclination_deg=0.470,
                lon_ascending_node_deg=219.106,
                arg_periapsis_deg=88.970,
                mean_anomaly_epoch_deg=171.016,
                orbital_period_days=3.551181,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=4.7998e22,
            radius_km=1560.8,
            style=VisualStyle(
                color_rgb=(215, 200, 175),
                radius_px=3,
                trail_color_rgb=(180, 170, 150),
            ),
            description="Galilean moon with a smooth water-ice crust over a subsurface ocean.",
        ),
        CelestialBody(
            name="Ganymede",
            category="moon",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=1070412.0 / AU_IN_KM,
                eccentricity=0.0013,
                inclination_deg=0.177,
                lon_ascending_node_deg=63.552,
                arg_periapsis_deg=192.417,
                mean_anomaly_epoch_deg=317.540,
                orbital_period_days=7.154552,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.4819e23,
            radius_km=2634.1,
            style=VisualStyle(
                color_rgb=(185, 175, 160),
                radius_px=3,
                trail_color_rgb=(155, 145, 135),
            ),
            description="Largest moon in the Solar System and third Galilean satellite.",
        ),
        CelestialBody(
            name="Callisto",
            category="moon",
            parent_name="Jupiter",
            elements=OrbitalElements(
                semi_major_axis_au=1882709.0 / AU_IN_KM,
                eccentricity=0.0074,
                inclination_deg=0.192,
                lon_ascending_node_deg=298.848,
                arg_periapsis_deg=52.643,
                mean_anomaly_epoch_deg=181.408,
                orbital_period_days=16.689018,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.0759e23,
            radius_km=2410.3,
            style=VisualStyle(
                color_rgb=(145, 135, 125),
                radius_px=3,
                trail_color_rgb=(120, 110, 100),
            ),
            description="Outermost Galilean moon with an ancient heavily cratered ice-rock surface.",
        ),
        CelestialBody(
            name="Titan",
            category="moon",
            parent_name="Saturn",
            elements=OrbitalElements(
                semi_major_axis_au=1221870.0 / AU_IN_KM,
                eccentricity=0.0288,
                inclination_deg=0.34854,
                lon_ascending_node_deg=28.06,
                arg_periapsis_deg=180.53,
                mean_anomaly_epoch_deg=163.31,
                orbital_period_days=15.94542,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.3452e23,
            radius_km=2574.7,
            style=VisualStyle(
                color_rgb=(235, 180, 95),
                radius_px=3,
                trail_color_rgb=(200, 150, 80),
            ),
            description="Largest moon of Saturn; possesses a dense nitrogen-methane atmosphere.",
        ),
        CelestialBody(
            name="Triton",
            category="moon",
            parent_name="Neptune",
            elements=OrbitalElements(
                semi_major_axis_au=354759.0 / AU_IN_KM,
                eccentricity=0.000016,
                inclination_deg=156.865,
                lon_ascending_node_deg=177.608,
                arg_periapsis_deg=293.09,
                mean_anomaly_epoch_deg=252.71,
                orbital_period_days=-5.876854,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=2.14e22,
            radius_km=1353.4,
            style=VisualStyle(
                color_rgb=(175, 215, 235),
                radius_px=3,
                trail_color_rgb=(145, 185, 205),
            ),
            description="Largest moon of Neptune; captured Kuiper belt object in a retrograde orbit.",
        ),
    )


def _build_dwarfs_and_comets() -> tuple[CelestialBody, ...]:
    """Construct the 4 main-belt dwarf/minor bodies and 3 periodic/long-period comets.

    Returns:
        7-element tuple containing Ceres, Vesta, Pallas, Hygiea, 1P/Halley, 2P/Encke, and Hale-Bopp.
    """
    return (
        CelestialBody(
            name="Ceres",
            category="dwarf",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=2.7675,
                eccentricity=0.07582,
                inclination_deg=10.593,
                lon_ascending_node_deg=80.329,
                arg_periapsis_deg=73.597,
                mean_anomaly_epoch_deg=95.989,
                orbital_period_days=1681.63,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=9.3835e20,
            radius_km=469.7,
            style=VisualStyle(
                color_rgb=(185, 180, 170),
                radius_px=4,
                trail_color_rgb=(150, 145, 135),
            ),
            description="Largest object and dwarf planet in the main asteroid belt.",
        ),
        CelestialBody(
            name="Vesta",
            category="dwarf",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=2.36179,
                eccentricity=0.08874,
                inclination_deg=7.140,
                lon_ascending_node_deg=103.851,
                arg_periapsis_deg=151.198,
                mean_anomaly_epoch_deg=20.864,
                orbital_period_days=1325.75,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=2.59076e20,
            radius_km=262.7,
            style=VisualStyle(
                color_rgb=(200, 190, 175),
                radius_px=3,
                trail_color_rgb=(160, 150, 140),
            ),
            description="Differentiated protoplanet in the inner main asteroid belt.",
        ),
        CelestialBody(
            name="Pallas",
            category="dwarf",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=2.77247,
                eccentricity=0.2313,
                inclination_deg=34.841,
                lon_ascending_node_deg=173.096,
                arg_periapsis_deg=310.049,
                mean_anomaly_epoch_deg=78.228,
                orbital_period_days=1686.15,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=2.04e20,
            radius_km=256.0,
            style=VisualStyle(
                color_rgb=(175, 185, 195),
                radius_px=3,
                trail_color_rgb=(140, 150, 160),
            ),
            description="Large main-belt asteroid on a highly inclined, eccentric orbit.",
        ),
        CelestialBody(
            name="Hygiea",
            category="dwarf",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=3.1421,
                eccentricity=0.1146,
                inclination_deg=3.831,
                lon_ascending_node_deg=283.20,
                arg_periapsis_deg=312.32,
                mean_anomaly_epoch_deg=156.35,
                orbital_period_days=2034.4,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=8.74e19,
            radius_km=217.0,
            style=VisualStyle(
                color_rgb=(155, 150, 145),
                radius_px=3,
                trail_color_rgb=(125, 120, 115),
            ),
            description="Fourth-largest main-belt asteroid in the outer carbonaceous belt.",
        ),
        CelestialBody(
            name="1P/Halley",
            category="comet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=17.834,
                eccentricity=0.96714,
                inclination_deg=162.26,
                lon_ascending_node_deg=58.42,
                arg_periapsis_deg=111.33,
                mean_anomaly_epoch_deg=38.38,
                orbital_period_days=-27510.0,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=2.2e14,
            radius_km=5.5,
            style=VisualStyle(
                color_rgb=(140, 235, 255),
                radius_px=3,
                trail_color_rgb=(100, 200, 240),
            ),
            description="Archetypal retrograde Halley-type periodic comet (~75.3-year period).",
        ),
        CelestialBody(
            name="2P/Encke",
            category="comet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=2.215,
                eccentricity=0.84830,
                inclination_deg=11.78,
                lon_ascending_node_deg=334.57,
                arg_periapsis_deg=186.54,
                mean_anomaly_epoch_deg=160.0,
                orbital_period_days=1204.2,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=8.0e13,
            radius_km=2.4,
            style=VisualStyle(
                color_rgb=(120, 245, 220),
                radius_px=3,
                trail_color_rgb=(90, 210, 185),
            ),
            description="Short-period comet with the shortest orbital period (~3.3 years) of any bright comet.",
        ),
        CelestialBody(
            name="Hale-Bopp",
            category="comet",
            parent_name="Sun",
            elements=OrbitalElements(
                semi_major_axis_au=186.0,
                eccentricity=0.995086,
                inclination_deg=89.43,
                lon_ascending_node_deg=282.47,
                arg_periapsis_deg=130.59,
                mean_anomaly_epoch_deg=0.45,
                orbital_period_days=926000.0,
                epoch_jd=J2000_EPOCH_JD,
            ),
            mass_kg=1.3e16,
            radius_km=30.0,
            style=VisualStyle(
                color_rgb=(190, 230, 255),
                radius_px=3,
                trail_color_rgb=(150, 200, 245),
            ),
            description="Great Comet C/1995 O1 on a near-perpendicular, extreme-eccentricity orbit.",
        ),
    )


def build_named_bodies() -> tuple[CelestialBody, ...]:
    """Construct the canonical 25-body J2000 solar system catalog.

    Returns:
        Immutable 25-element tuple containing the Sun, 8 planets, 9 moons,
        4 main-belt dwarf/minor bodies, and 3 comets.
    """
    return _build_star_and_planets() + _build_moons() + _build_dwarfs_and_comets()


def is_in_kirkwood_gap(
    semi_major_axis_au: float,
    gaps: tuple[KirkwoodGap, ...] = KIRKWOOD_GAPS,
) -> bool:
    """Return ``True`` if ``semi_major_axis_au`` lies inside any Kirkwood gap exclusion zone.

    Args:
        semi_major_axis_au: Candidate semi-major axis in Astronomical Units.
        gaps: Tuple of ``KirkwoodGap`` definitions to test against.

    Returns:
        ``True`` when ``abs(semi_major_axis_au - gap.center_au) <= gap.half_width_au + 1e-12``
        for at least one gap in ``gaps``, else ``False``.
    """
    for gap in gaps:
        if abs(semi_major_axis_au - gap.center_au) <= gap.half_width_au + 1e-12:
            return True
    return False


def generate_asteroid_belt(
    count: int = 360,
    seed: int = 42,
) -> tuple[CelestialBody, ...]:
    """Generate a deterministic main asteroid belt using Kirkwood gap rejection sampling.

    # IMPLEMENTATION DECISION: Instantiate an isolated random.Random(seed) instance
    # and reject candidate semi-major axes in [2.10, 3.35] AU that fall within any of
    # KIRKWOOD_GAPS before drawing the remaining orbital elements (e, i, Omega, omega, M0).
    # Rationale: Guarantees bit-for-bit reproducibility across repeated calls without
    # mutating global random state and ensures zero asteroids occupy resonant gaps.
    # Alternatives: Piecewise inverse-CDF sampling across inter-gap intervals.

    Args:
        count: Number of asteroids to generate (must be ``>= 0``, default ``360``).
        seed: Integer PRNG seed for deterministic generation (default ``42``).

    Returns:
        Immutable tuple of ``count`` ``CelestialBody`` instances with ``category="asteroid"``.

    Raises:
        ValueError: If ``count < 0``.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if count == 0:
        return ()

    rng = random.Random(seed)
    asteroids: list[CelestialBody] = []
    asteroid_style = VisualStyle(
        color_rgb=(135, 130, 125),
        radius_px=1,
        trail_color_rgb=(95, 90, 85),
    )

    while len(asteroids) < count:
        candidate_a = rng.uniform(2.10, 3.35)
        if is_in_kirkwood_gap(candidate_a, KIRKWOOD_GAPS):
            continue

        e = rng.uniform(0.02, 0.22)
        i_deg = rng.uniform(0.0, 15.0)
        lon_node_deg = rng.uniform(0.0, 360.0)
        arg_peri_deg = rng.uniform(0.0, 360.0)
        mean_anom_deg = rng.uniform(0.0, 360.0)
        period_days = EARTH_SIDEREAL_YEAR_DAYS * (candidate_a**1.5)
        index_number = len(asteroids) + 1

        elements = OrbitalElements(
            semi_major_axis_au=candidate_a,
            eccentricity=e,
            inclination_deg=i_deg,
            lon_ascending_node_deg=lon_node_deg,
            arg_periapsis_deg=arg_peri_deg,
            mean_anomaly_epoch_deg=mean_anom_deg,
            orbital_period_days=period_days,
            epoch_jd=J2000_EPOCH_JD,
        )

        asteroids.append(
            CelestialBody(
                name=f"Asteroid-{index_number:04d}",
                category="asteroid",
                parent_name="Sun",
                elements=elements,
                mass_kg=1.0e15,
                radius_km=5.0,
                style=asteroid_style,
                description="Main-belt asteroid outside resonant Jupiter Kirkwood gaps.",
            )
        )

    return tuple(asteroids)


def build_catalog(
    asteroid_count: int = 360,
    seed: int = 42,
) -> tuple[CelestialBody, ...]:
    """Build the complete solar system catalog combining named bodies and belt asteroids.

    Args:
        asteroid_count: Number of procedural main-belt asteroids to include (default ``360``).
        seed: PRNG seed for deterministic asteroid belt generation (default ``42``).

    Returns:
        Tuple containing the 25 named J2000 bodies followed by ``asteroid_count`` asteroids.
    """
    return build_named_bodies() + generate_asteroid_belt(count=asteroid_count, seed=seed)