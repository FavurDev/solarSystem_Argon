"""Headless unit tests for OrbitPoint and TrailBuffer bounded ring buffer."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError

import pytest
from solar_system.trail import OrbitPoint, TrailBuffer


def test_orbit_point_dataclass_fields_frozen_and_slots() -> None:
    """Verify OrbitPoint stores coordinates and JD with frozen, slotted semantics."""
    # Arrange
    pt = OrbitPoint(x_au=1.0, y_au=-0.5, jd=2451545.0)
    same_pt = OrbitPoint(x_au=1.0, y_au=-0.5, jd=2451545.0)
    different_pt = OrbitPoint(x_au=1.0, y_au=0.5, jd=2451545.0)

    # Act & Assert
    assert pt.x_au == 1.0
    assert pt.y_au == -0.5
    assert pt.jd == 2451545.0
    assert pt == same_pt
    assert pt != different_pt
    assert hash(pt) == hash(same_pt)
    assert not hasattr(pt, "__dict__")

    with pytest.raises(FrozenInstanceError):
        pt.x_au = 2.0  # type: ignore[misc]

    with pytest.raises((AttributeError, TypeError)):
        pt.extra = 1  # type: ignore[attr-defined]


def test_trail_buffer_default_and_custom_initialization() -> None:
    """Verify TrailBuffer initializes default and custom capacity and frame_name."""
    # Arrange & Act
    default_buf = TrailBuffer()
    custom_buf = TrailBuffer(max_points=120, frame_name="Earth")

    # Assert
    assert default_buf.max_points == 480
    assert default_buf.frame_name == "Sun"
    assert len(default_buf) == 0
    assert default_buf.points() == ()

    assert custom_buf.max_points == 120
    assert custom_buf.frame_name == "Earth"
    assert len(custom_buf) == 0
    assert custom_buf.points() == ()


def test_trail_buffer_properties_are_read_only() -> None:
    """Verify max_points and frame_name are read-only properties on TrailBuffer."""
    # Arrange
    buf = TrailBuffer()

    # Act & Assert
    with pytest.raises(AttributeError):
        buf.max_points = 10  # type: ignore[misc]

    with pytest.raises(AttributeError):
        buf.frame_name = "Mars"  # type: ignore[misc]


def test_trail_buffer_caps_capacity_at_480_after_1000_appends_fifo_order() -> None:
    """Verify appending 1,000 samples caps len at 480 and retains 520..999 in FIFO order."""
    # Arrange
    buffer = TrailBuffer(max_points=480, frame_name="Sun")

    # Act
    for i in range(1000):
        buffer.append(
            x_au=float(i),
            y_au=float(-i),
            jd=2451545.0 + float(i),
            frame_name="Sun",
        )
    pts = buffer.points()

    # Assert
    assert len(buffer) == 480
    assert isinstance(pts, tuple)
    assert len(pts) == 480
    assert pts[0] == OrbitPoint(x_au=520.0, y_au=-520.0, jd=2451545.0 + 520.0)
    assert pts[-1] == OrbitPoint(x_au=999.0, y_au=-999.0, jd=2451545.0 + 999.0)
    expected = tuple(
        OrbitPoint(x_au=float(k), y_au=float(-k), jd=2451545.0 + float(k))
        for k in range(520, 1000)
    )
    assert pts == expected


def test_trail_buffer_minimum_valid_capacity_of_two() -> None:
    """Verify minimum valid capacity max_points=2 retains the 2 most recent samples."""
    # Arrange
    buf = TrailBuffer(max_points=2, frame_name="Sun")

    # Act
    buf.append(x_au=1.0, y_au=0.0, jd=1.0, frame_name="Sun")
    buf.append(x_au=2.0, y_au=0.5, jd=2.0, frame_name="Sun")
    buf.append(x_au=3.0, y_au=1.0, jd=3.0, frame_name="Sun")
    pts = buf.points()

    # Assert
    assert len(buf) == 2
    assert [p.jd for p in pts] == [2.0, 3.0]
    assert pts == (
        OrbitPoint(x_au=2.0, y_au=0.5, jd=2.0),
        OrbitPoint(x_au=3.0, y_au=1.0, jd=3.0),
    )


def test_trail_buffer_append_clears_prior_points_on_frame_switch_to_mars() -> None:
    """Verify frame switch from Sun to Mars clears prior points and retains only Mars point."""
    # Arrange
    buffer = TrailBuffer(max_points=480, frame_name="Sun")
    for i in range(50):
        buffer.append(
            x_au=float(i) * 0.1,
            y_au=float(i) * 0.2,
            jd=2451545.0 + float(i),
            frame_name="Sun",
        )
    assert len(buffer) == 50

    # Act
    buffer.append(x_au=1.524, y_au=0.0, jd=2451600.0, frame_name="Mars")

    # Assert
    assert len(buffer) == 1
    assert buffer.frame_name == "Mars"
    assert buffer.points() == (OrbitPoint(x_au=1.524, y_au=0.0, jd=2451600.0),)


def test_trail_buffer_multiple_frame_switches_sun_to_earth_to_mars() -> None:
    """Verify multiple reference-frame transitions and frame switch on an empty buffer."""
    # Arrange
    buffer = TrailBuffer(max_points=10, frame_name="Sun")
    for i in range(3):
        buffer.append(x_au=float(i), y_au=0.0, jd=100.0 + float(i), frame_name="Sun")
    assert len(buffer) == 3

    # Act & Assert: switch from Sun to Earth
    buffer.append(x_au=0.002, y_au=0.001, jd=103.0, frame_name="Earth")
    buffer.append(x_au=0.001, y_au=0.002, jd=104.0, frame_name="Earth")
    assert buffer.frame_name == "Earth"
    assert len(buffer) == 2

    # Act & Assert: switch from Earth to Mars
    buffer.append(x_au=1.5, y_au=-0.2, jd=105.0, frame_name="Mars")
    assert buffer.frame_name == "Mars"
    assert len(buffer) == 1
    assert buffer.points() == (OrbitPoint(x_au=1.5, y_au=-0.2, jd=105.0),)

    # Act & Assert: frame switch on an already-empty buffer
    empty_buf = TrailBuffer(max_points=10, frame_name="Sun")
    empty_buf.append(x_au=5.2, y_au=0.1, jd=200.0, frame_name="Jupiter")
    assert empty_buf.frame_name == "Jupiter"
    assert len(empty_buf) == 1
    assert empty_buf.points() == (OrbitPoint(x_au=5.2, y_au=0.1, jd=200.0),)


def test_trail_buffer_clear_resets_length_and_preserves_frame_and_capacity() -> None:
    """Verify clear() resets length to 0, preserves capacity and frame, and is idempotent."""
    # Arrange
    buffer = TrailBuffer(max_points=50, frame_name="Earth")
    for i in range(10):
        buffer.append(x_au=float(i), y_au=float(i), jd=2451545.0 + float(i), frame_name="Earth")
    assert len(buffer) == 10

    # Act
    buffer.clear()
    buffer.clear()

    # Assert
    assert len(buffer) == 0
    assert buffer.points() == ()
    assert buffer.max_points == 50
    assert buffer.frame_name == "Earth"

    # Subsequent append under same frame accumulates normally from length 1
    buffer.append(x_au=1.0, y_au=2.0, jd=2451600.0, frame_name="Earth")
    assert len(buffer) == 1


@pytest.mark.parametrize("invalid_max_points", [1, 0, -1, -480])
def test_trail_buffer_raises_value_error_when_max_points_less_than_two(
    invalid_max_points: int,
) -> None:
    """Verify TrailBuffer raises ValueError when initialized with max_points < 2."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="max_points"):
        TrailBuffer(max_points=invalid_max_points)


def test_trail_buffer_accepts_reverse_time_julian_dates() -> None:
    """Verify appending reverse-time decreasing Julian Dates preserves FIFO insertion order."""
    # Arrange
    buffer = TrailBuffer(max_points=5, frame_name="Sun")

    # Act
    buffer.append(x_au=1.0, y_au=0.0, jd=2451545.0, frame_name="Sun")
    buffer.append(x_au=0.98, y_au=-0.02, jd=2451544.0, frame_name="Sun")
    buffer.append(x_au=0.95, y_au=-0.04, jd=2451543.0, frame_name="Sun")

    # Assert
    assert len(buffer) == 3
    assert [p.jd for p in buffer.points()] == [2451545.0, 2451544.0, 2451543.0]


def test_trail_module_does_not_load_pygame_into_sys_modules() -> None:
    """Verify importing and exercising solar_system.trail does not load pygame."""
    # Arrange
    buf = TrailBuffer(max_points=4, frame_name="Sun")

    # Act
    buf.append(x_au=1.0, y_au=0.0, jd=2451545.0, frame_name="Sun")
    pts = buf.points()

    # Assert
    assert len(pts) == 1
    assert "solar_system.trail" in sys.modules
    assert "pygame" not in sys.modules