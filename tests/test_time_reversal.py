"""Headless unit tests for SimulationState clock and time-reversal invariance."""

from __future__ import annotations

import pytest

from solar_system.bodies import J2000_EPOCH_JD
from solar_system.simulation import SimulationState, jd_to_iso_date


def test_time_reversal_120_steps_restores_epoch_and_positions() -> None:
    """Verify 120 forward steps followed by 120 reverse steps restore J2000 epoch and positions."""
    # Arrange
    sim = SimulationState.create_default(
        asteroid_count=360,
        seed=42,
        initial_jd=J2000_EPOCH_JD,
    )
    initial_positions = dict(sim.cached_positions_au)
    assert sim.julian_date == J2000_EPOCH_JD
    assert sim.direction == 1

    # Act
    for _ in range(120):
        sim.step(dt_wall_sec=0.5)
    mid_jd = sim.julian_date
    reversed_dir = sim.reverse_direction()
    for _ in range(120):
        sim.step(dt_wall_sec=0.5)
    restored_dir = sim.reverse_direction()

    # Assert
    assert mid_jd > J2000_EPOCH_JD
    assert abs(mid_jd - (J2000_EPOCH_JD + 60.0)) < 1e-12
    assert reversed_dir == -1
    assert restored_dir == 1
    assert sim.direction == 1
    assert abs(sim.julian_date - J2000_EPOCH_JD) < 1e-12

    for body_name, init_pos in initial_positions.items():
        pos_drift_au = (sim.cached_positions_au[body_name] - init_pos).norm()
        assert pos_drift_au < 1e-9, (
            f"Position drift {pos_drift_au} AU exceeded 1e-9 AU for {body_name}"
        )

    for trail in sim.trails.values():
        assert len(trail) == 240


def test_time_reversal_invariance_in_non_heliocentric_frame_and_high_speed() -> None:
    """Verify 120 forward and 120 reverse steps in Mars frame at 10 d/s restore positions."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=60, seed=42)
    sim.set_reference_frame(frame_name="Mars")
    for _ in range(3):
        sim.speed_up()
    assert sim.current_speed_days_per_sec == 10.0
    initial_mars_frame_positions = dict(sim.cached_positions_au)

    # Act
    for _ in range(120):
        sim.step(dt_wall_sec=0.5)
    sim.reverse_direction()
    for _ in range(120):
        sim.step(dt_wall_sec=0.5)

    # Assert
    assert abs(sim.julian_date - J2000_EPOCH_JD) < 1e-12
    for body_name, init_pos in initial_mars_frame_positions.items():
        drift = (sim.cached_positions_au[body_name] - init_pos).norm()
        assert drift < 1e-9, f"Mars-frame drift {drift} AU exceeded 1e-9 AU for {body_name}"


def test_state_at_is_pure_and_matches_step_positions() -> None:
    """Verify state_at is pure without mutating state, centers frame origin, and validates args."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=32, seed=42)
    target_jd = J2000_EPOCH_JD + 45.25

    # Act
    queried_positions = sim.state_at(jd=target_jd, frame_name="Earth")
    default_frame_positions = sim.state_at(jd=target_jd)

    # Assert
    assert sim.julian_date == J2000_EPOCH_JD
    assert sim.active_frame_name == "Sun"
    for trail in sim.trails.values():
        assert len(trail) == 0
    assert queried_positions["Earth"].norm() < 1e-12
    assert default_frame_positions["Sun"].norm() < 1e-12

    sim.step(dt_wall_sec=45.25)
    for body_name, stepped_pos in sim.cached_positions_au.items():
        assert (default_frame_positions[body_name] - stepped_pos).norm() < 1e-12

    with pytest.raises(KeyError):
        sim.state_at(J2000_EPOCH_JD, "InvalidFrame")

    with pytest.raises(ValueError):
        sim.state_at(float("nan"))


def test_toggle_pause_freezes_step_and_trails() -> None:
    """Verify toggle_pause freezes step progression and trail recording while paused."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=32, seed=42)
    sim.step(dt_wall_sec=1.0)
    jd_before = sim.julian_date
    positions_before = dict(sim.cached_positions_au)
    earth_trail_len_before = len(sim.trails["Earth"])

    # Act
    paused_state = sim.toggle_pause()
    paused_flag_during = sim.paused
    sim.step(dt_wall_sec=10.0)
    unpaused_state = sim.toggle_pause()

    # Assert
    assert paused_state is True
    assert paused_flag_during is True
    assert sim.julian_date == jd_before
    assert sim.cached_positions_au == positions_before
    assert len(sim.trails["Earth"]) == earth_trail_len_before
    assert unpaused_state is False
    assert sim.paused is False


def test_step_zero_dt_is_noop_and_negative_or_nonfinite_dt_raises() -> None:
    """Verify step(0.0) is a no-op and negative or non-finite dt_wall_sec raises ValueError."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=32, seed=42)

    # Act
    positions = sim.step(dt_wall_sec=0.0)

    # Assert
    assert sim.julian_date == J2000_EPOCH_JD
    assert len(sim.trails["Earth"]) == 0
    assert positions == sim.cached_positions_au

    with pytest.raises(ValueError):
        sim.step(-0.1)

    with pytest.raises(ValueError):
        sim.step(float("nan"))

    with pytest.raises(ValueError):
        sim.step(float("inf"))

    with pytest.raises(ValueError):
        sim.step(float("-inf"))


def test_reset_epoch_restores_j2000_direction_and_clears_trails() -> None:
    """Verify reset_epoch restores initial_jd, direction=+1, J2000 positions, and empty trails."""
    # Arrange
    sim = SimulationState.create_default(asteroid_count=32, seed=42)
    sim.step(dt_wall_sec=5.0)
    sim.reverse_direction()
    sim.step(dt_wall_sec=1.0)
    assert sim.julian_date != J2000_EPOCH_JD
    assert sim.direction == -1
    assert len(sim.trails["Earth"]) == 2

    # Act
    sim.reset_epoch()

    # Assert
    assert sim.julian_date == J2000_EPOCH_JD
    assert sim.direction == 1
    for trail in sim.trails.values():
        assert len(trail) == 0
    expected_positions = sim.state_at(J2000_EPOCH_JD, sim.active_frame_name)
    for body_name, pos in expected_positions.items():
        assert (sim.cached_positions_au[body_name] - pos).norm() < 1e-12


def test_jd_to_iso_date_formatting() -> None:
    """Verify jd_to_iso_date formats Julian Dates as YYYY-MM-DD and rejects non-finite values."""
    # Arrange & Act & Assert
    assert jd_to_iso_date(2451545.0) == "2000-01-01"
    assert jd_to_iso_date(2451545.49) == "2000-01-01"
    assert jd_to_iso_date(2451546.0) == "2000-01-02"
    assert jd_to_iso_date(2451544.0) == "1999-12-31"
    assert jd_to_iso_date(2451911.0) == "2001-01-01"

    with pytest.raises(ValueError):
        jd_to_iso_date(float("nan"))

    with pytest.raises(ValueError):
        jd_to_iso_date(float("inf"))
