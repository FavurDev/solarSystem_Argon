"""Verification tests for visual-proof PNG screenshots, visual-proof/README.md, and root README.md."""

from __future__ import annotations

import importlib
import struct
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISUAL_PROOF_DIR = PROJECT_ROOT / "visual-proof"
VISUAL_PROOF_README = VISUAL_PROOF_DIR / "README.md"
ROOT_README = PROJECT_ROOT / "README.md"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_WIDTH = 1440
EXPECTED_HEIGHT = 1080

EXPECTED_SCREENSHOTS: tuple[str, ...] = (
    "01_first_light.png",
    "02_title_scene.png",
    "03_simulation_scene.png",
    "04_paused_scene.png",
    "05_before_reversal.png",
    "06_after_reversal.png",
    "07_rate_change.png",
)


def _read_png_ihdr_dimensions(png_path: Path) -> tuple[int, int]:
    """Verify PNG 8-byte signature and return (width, height) from the IHDR chunk."""
    raw = png_path.read_bytes()
    assert len(raw) >= 24, f"PNG file too short ({len(raw)} bytes): {png_path}"
    assert raw[:8] == PNG_SIGNATURE, f"Invalid PNG signature in {png_path.name}"
    chunk_length, chunk_type, width, height = struct.unpack(">I4sII", raw[8:24])
    assert chunk_length == 13, f"Unexpected IHDR length {chunk_length} in {png_path.name}"
    assert chunk_type == b"IHDR", f"First chunk is not IHDR in {png_path.name}: {chunk_type!r}"
    return width, height


@pytest.mark.parametrize("filename", EXPECTED_SCREENSHOTS)
def test_visual_proof_png_signature_and_ihdr_dimensions(filename: str) -> None:
    """Each of the 7 visual-proof PNGs must exist, have a valid PNG header, and measure 1440x1080."""
    png_path = VISUAL_PROOF_DIR / filename
    assert png_path.exists(), f"Missing visual-proof screenshot: {png_path}"
    assert png_path.stat().st_size > 10_000, f"Screenshot suspiciously small: {png_path}"
    width, height = _read_png_ihdr_dimensions(png_path)
    assert (width, height) == (EXPECTED_WIDTH, EXPECTED_HEIGHT), (
        f"Expected 1440x1080 IHDR dimensions for {filename}, got {width}x{height}"
    )


def test_visual_proof_pngs_contain_non_uniform_rendered_pixels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 7 screenshots must contain rich non-uniform rendered pixel content and distinct states."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    preloaded_keys = set(sys.modules)
    pygame: Any = None
    try:
        pygame = importlib.import_module("pygame")
        pygame.init()
        file_bytes: dict[str, bytes] = {}
        for filename in EXPECTED_SCREENSHOTS:
            png_path = VISUAL_PROOF_DIR / filename
            file_bytes[filename] = png_path.read_bytes()
            surface = pygame.image.load(str(png_path))
            assert surface.get_size() == (EXPECTED_WIDTH, EXPECTED_HEIGHT)

            distinct_colors: set[tuple[int, int, int]] = set()
            for x in range(0, EXPECTED_WIDTH, 20):
                for y in range(0, EXPECTED_HEIGHT, 20):
                    color = surface.get_at((x, y))
                    distinct_colors.add((color.r, color.g, color.b))
            assert len(distinct_colors) >= 12, (
                f"{filename} lacks rendered pixel diversity (found {len(distinct_colors)} colors)"
            )

        # Ensure progressive scenes differ visually across state transitions and epoch changes
        assert file_bytes["02_title_scene.png"] != file_bytes["03_simulation_scene.png"]
        assert file_bytes["03_simulation_scene.png"] != file_bytes["04_paused_scene.png"]
        assert file_bytes["05_before_reversal.png"] != file_bytes["06_after_reversal.png"]
        assert file_bytes["06_after_reversal.png"] != file_bytes["07_rate_change.png"]
    finally:
        if pygame is not None:
            pygame.quit()
        for mod_name in list(sys.modules):
            if (
                mod_name == "pygame"
                or mod_name.startswith("pygame.")
                or mod_name not in preloaded_keys
            ):
                sys.modules.pop(mod_name, None)


def test_visual_proof_readme_catalogs_all_seven_screenshots() -> None:
    """visual-proof/README.md must exist, be non-empty, and document all 7 screenshots and metadata."""
    assert VISUAL_PROOF_README.exists(), f"Missing visual-proof manifest: {VISUAL_PROOF_README}"
    content = VISUAL_PROOF_README.read_text(encoding="utf-8")
    assert len(content.strip()) > 500, "visual-proof/README.md is unexpectedly short"

    for filename in EXPECTED_SCREENSHOTS:
        assert filename in content, f"visual-proof/README.md missing reference to {filename}"

    expected_epochs = (
        "2451545.00",
        "2000-01-01",
        "2451565.00",
        "2000-01-21",
        "2451585.00",
        "2000-02-10",
        "2451575.00",
        "2000-01-31",
        "2451620.00",
        "2000-03-16",
    )
    for token in expected_epochs:
        assert token in content, f"visual-proof/README.md missing expected epoch token {token!r}"

    expected_rates_and_inputs = (
        "+1.00 d/s",
        "+10.00 d/s",
        "-10.00 d/s",
        "+90.00 d/s",
        "+1",
        "-1",
        "KEY_RETURN",
        "KEY_PLUS",
        "KEY_P",
        "KEY_SPACE",
    )
    for token in expected_rates_and_inputs:
        assert token in content, f"visual-proof/README.md missing expected metadata token {token!r}"


def test_root_readme_contains_required_commands_constants_and_controls() -> None:
    """Root README.md must document build/test/launch commands, scaling constants, and controls."""
    assert ROOT_README.exists(), f"Missing root README.md: {ROOT_README}"
    content = ROOT_README.read_text(encoding="utf-8")
    assert len(content.strip()) > 500, "Root README.md is unexpectedly short"

    required_commands = (
        "poetry install",
        "poetry run ruff check .",
        "poetry run mypy src tests",
        "poetry run pytest",
        "poetry run solar-system",
        "Python 3.11+",
    )
    for cmd in required_commands:
        assert cmd in content, f"Root README.md missing required command/version {cmd!r}"

    required_scaling_constants = (
        "0.30",
        "375.0",
        "52.0",
        "500.0",
        "720",
        "540",
        "16.0",
        "28.0",
    )
    for const in required_scaling_constants:
        assert const in content, f"Root README.md missing scaling constant {const!r}"

    required_controls = (
        "ENTER",
        "SPACE",
        "P",
        "+",
        "-",
        "R",
        "TAB",
        "1",
        "2",
        "3",
        "4",
        "5",
        "[",
        "]",
        "ESC",
    )
    for key in required_controls:
        assert key in content, f"Root README.md missing keyboard control {key!r}"
