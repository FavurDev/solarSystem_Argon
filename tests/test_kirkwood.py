"""Headless unit tests for Kirkwood resonance gaps and seeded asteroid belt generation."""

from __future__ import annotations

import pytest

from solar_system.bodies import (
    J2000_EPOCH_JD,
    JUPITER_PERIOD_DAYS,
    KIRKWOOD_GAPS,
    KirkwoodGap,
    build_catalog,
    generate_asteroid_belt,
    is_in_kirkwood_gap,
)


def test_kirkwood_gaps_constants_and_resonances() -> None:
    """Verify KIRKWOOD_GAPS defines the 5 mean-motion resonances with Jupiter."""
    # Arrange
    expected_resonances = {
        "4:1": (4, 1, 2.065, 0.025),
        "3:1": (3, 1, 2.502, 0.035),
        "5:2": (5, 2, 2.825, 0.030),
        "7:3": (7, 3, 2.958, 0.022),
        "2:1": (2, 1, 3.278, 0.040),
    }

    # Act
    gaps_by_name = {gap.label: gap for gap in KIRKWOOD_GAPS}

    # Assert
    assert J2000_EPOCH_JD == 2451545.0
    assert JUPITER_PERIOD_DAYS == 4332.589
    assert len(KIRKWOOD_GAPS) == 5
    assert set(gaps_by_name.keys()) == set(expected_resonances.keys())
    for label, (ratio_num, ratio_den, center_au, half_width_au) in expected_resonances.items():
        gap = gaps_by_name[label]
        assert isinstance(gap, KirkwoodGap)
        assert gap.label == label
        assert gap.resonance == label
        assert gap.ratio_num == ratio_num
        assert gap.ratio_den == ratio_den
        assert gap.center_au == pytest.approx(center_au, abs=1e-9)
        assert gap.half_width_au == pytest.approx(half_width_au, abs=1e-9)


def test_is_in_kirkwood_gap_detects_interior_and_boundary_points() -> None:
    """Verify is_in_kirkwood_gap returns True inside/at boundaries and False outside."""
    # Arrange
    safe_semi_major_axes = (2.15, 2.35, 2.65, 2.90, 3.10)

    # Act & Assert
    for gap in KIRKWOOD_GAPS:
        assert is_in_kirkwood_gap(gap.center_au) is True
        assert is_in_kirkwood_gap(gap.center_au - gap.half_width_au) is True
        assert is_in_kirkwood_gap(gap.center_au + gap.half_width_au) is True
        assert is_in_kirkwood_gap(gap.center_au - gap.half_width_au - 1e-4) is False
        assert is_in_kirkwood_gap(gap.center_au + gap.half_width_au + 1e-4) is False

    for a_au in safe_semi_major_axes:
        assert is_in_kirkwood_gap(a_au) is False

    assert is_in_kirkwood_gap(2.502, gaps=()) is False


def test_generate_asteroid_belt_is_deterministic_for_seed_42() -> None:
    """Verify generate_asteroid_belt(360, seed=42) produces identical tuples across calls."""
    # Arrange / Act
    belt_run_1 = generate_asteroid_belt(count=360, seed=42)
    belt_run_2 = generate_asteroid_belt(count=360, seed=42)
    belt_seed_99 = generate_asteroid_belt(count=360, seed=99)

    # Assert
    assert len(belt_run_1) == 360
    assert belt_run_1 == belt_run_2
    assert belt_run_1 != belt_seed_99


def test_generate_asteroid_belt_has_zero_asteroids_in_kirkwood_gaps() -> None:
    """Verify all 360 generated asteroids strictly avoid the 5 Kirkwood gap exclusion zones."""
    # Arrange / Act
    asteroids = generate_asteroid_belt(count=360, seed=42)

    # Assert
    assert len(asteroids) == 360
    for asteroid in asteroids:
        assert asteroid.category == "asteroid"
        assert asteroid.parent_name == "Sun"
        assert asteroid.elements is not None
        a_au = asteroid.elements.semi_major_axis_au
        assert 2.10 <= a_au <= 3.35
        assert is_in_kirkwood_gap(a_au) is False
        for gap in KIRKWOOD_GAPS:
            assert abs(a_au - gap.center_au) > gap.half_width_au


def test_generate_asteroid_belt_populates_all_inter_gap_zones() -> None:
    """Verify every inter-gap belt region between 2.10 and 3.238 AU has > 0 asteroids."""
    # Arrange
    inter_gap_zones = (
        ("zone_1_between_4_1_and_3_1", 2.100, 2.467),
        ("zone_2_between_3_1_and_5_2", 2.537, 2.795),
        ("zone_3_between_5_2_and_7_3", 2.855, 2.936),
        ("zone_4_between_7_3_and_2_1", 2.980, 3.238),
    )

    # Act
    asteroids = generate_asteroid_belt(count=360, seed=42)
    semi_major_axes = [
        body.elements.semi_major_axis_au
        for body in asteroids
        if body.elements is not None
    ]

    # Assert
    for zone_name, low_au, high_au in inter_gap_zones:
        zone_count = sum(1 for a_au in semi_major_axes if low_au <= a_au <= high_au)
        assert zone_count > 0, f"Expected > 0 asteroids in {zone_name}, got {zone_count}"


def test_generate_asteroid_belt_edge_cases_and_build_catalog() -> None:
    """Verify zero/negative asteroid counts and full catalog assembly via build_catalog."""
    # Arrange / Act
    empty_belt = generate_asteroid_belt(count=0, seed=42)
    catalog = build_catalog(asteroid_count=360, seed=42)

    # Assert
    assert empty_belt == ()
    assert len(catalog) == 25 + 360
    with pytest.raises(ValueError, match="count"):
        generate_asteroid_belt(count=-1, seed=42)
