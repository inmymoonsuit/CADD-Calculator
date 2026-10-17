"""The welcome screen's geometry, placed from its tokens (ADR-0015 §3, ADR-0016)."""

from __future__ import annotations

import pytest

from caddcalc.gui.welcome_layout import (
    Rect,
    Size,
    contain_fit,
    cover_crop,
    device_line,
    display_pixels,
    fit_scale,
    logo_box,
    pane_rect,
    scaled,
)
from caddcalc.gui.welcome_style import style

SLOT = style().art.slot


def test_art_of_the_slots_shape_is_shown_whole() -> None:
    assert cover_crop(Size(1920, 1080), SLOT) == Rect(0, 0, 1920, 1080)


def test_wide_art_is_cropped_at_the_sides_around_its_focus() -> None:
    crop = cover_crop(Size(3200, 1080), SLOT, (0.35, 0.5))
    assert (crop.width, crop.height, crop.y) == (1920, 1080, 0)
    assert crop.x == pytest.approx(0.35 * 3200 - 960)


def test_tall_art_is_cropped_top_and_bottom() -> None:
    crop = cover_crop(Size(1080, 1080), SLOT)
    assert (crop.x, crop.width) == (0, 1080)
    assert crop.height == pytest.approx(607.5)
    assert crop.y == pytest.approx((1080 - 607.5) / 2)


@pytest.mark.parametrize(("focus", "x"), [((0.0, 0.5), 0.0), ((1.0, 0.5), 3200 - 1920)])
def test_a_focus_near_an_edge_keeps_the_crop_inside_the_art(
    focus: tuple[float, float], x: float
) -> None:
    assert cover_crop(Size(3200, 1080), SLOT, focus).x == x


def test_the_screen_shrinks_to_fit_a_small_screen_and_never_grows() -> None:
    window = style().window
    assert fit_scale(Size(1920, 1040)) == 1.0
    small = fit_scale(Size(911, 512))  # 1366 x 768 at 150%, less a taskbar
    assert small == pytest.approx(min(911 / window.width, 512 / window.height))
    assert window.width * small <= 911 and window.height * small <= 512


@pytest.mark.parametrize(
    ("source", "fitted"),
    [
        (Size(72, 540), Rect(36, 0, 48, 360)),  # a tall banner: full height, centred
        (Size(100, 100), Rect(10, 130, 100, 100)),  # a square mark: full width
        (Size(400, 100), Rect(10, 167.5, 100, 25)),  # a wide wordmark: small and centred
    ],
)
def test_a_logo_is_contained_in_its_box_whole_and_centred(source: Size, fitted: Rect) -> None:
    assert contain_fit(source, Rect(10, 0, 100, 360)) == fitted


AREA = Rect(16, 16, 80, 508)
"""The shipped logo area: the logo region less its margins."""


@pytest.mark.parametrize(
    ("logo", "box"),
    [
        (Size(72, 540), Rect(30.19, 110, 51.61, 320)),  # a tall banner: capped at 320
        (Size(256, 256), Rect(16, 230, 80, 80)),  # a square mark, the app icon: 80 × 80
        (Size(400, 100), Rect(16, 246, 80, 48)),  # a wordmark: the least short side
        (Size(10, 540), Rect(32, 110, 48, 320)),  # a sliver: least short, greatest long
    ],
)
def test_the_logo_box_takes_the_logos_shape_within_its_limits(logo: Size, box: Rect) -> None:
    assert logo_box(logo, AREA, 8, 48, 320) == pytest.approx(box, abs=0.01)


def test_the_logo_area_is_the_logo_region_less_its_margins() -> None:
    tokens = style()
    assert tokens.logo_area == AREA
    assert scaled(AREA, 0.5) == Rect(8, 8, 40, 254)


@pytest.mark.parametrize(
    ("anchor", "corner"),
    [
        ("top_left", (6, 6)),
        ("top_right", (894, 6)),
        ("bottom_left", (6, 514)),
        ("bottom_right", (894, 514)),
    ],
)
def test_a_pane_sits_inset_from_its_anchor_corner(anchor: str, corner: tuple[int, int]) -> None:
    rect = pane_rect(anchor, 6, Size(60, 20), SLOT)
    assert (rect.x, rect.y, rect.width, rect.height) == (*corner, 60, 20)


@pytest.mark.parametrize(("ratio", "grid"), [(1, 2), (1.25, 2), (1.5, 3), (2, 4)])
def test_the_display_face_snaps_to_its_pixel_grid(ratio: float, grid: int) -> None:
    """50 px of a 25-pixel em: 2 device pixels per design pixel at 100%, 4 at 200%."""
    assert display_pixels(50, 1, ratio, 25) == grid
    assert display_pixels(50, 0.1, 1, 25) == 1, "never smaller than its own grid"


@pytest.mark.parametrize(("ratio", "device"), [(1, 1), (1.25, 1), (1.5, 2), (2, 2), (3, 3)])
def test_a_line_is_whole_device_pixels(ratio: float, device: int) -> None:
    assert device_line(1, ratio) == device
    assert device_line(0.4, 1) == 1, "never under one device pixel"
    assert device_line(0, ratio) == 0, "no line"


@pytest.mark.parametrize(("ratio", "grid"), [(1.25, 2), (1.75, 3)])
def test_a_tie_rounds_down_to_keep_the_title_in_its_safe_area(ratio: float, grid: int) -> None:
    """2.5 design-pixel multiples round to 2 and 3.5 to 3, where round-half-even gives 4."""
    assert display_pixels(50, 1, ratio, 25) == grid
    assert display_pixels(50, 1, 1.26, 25) == 3, "past the tie, it rounds up"
