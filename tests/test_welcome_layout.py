"""The welcome screen's geometry, placed from its tokens (ADR-0015 §3, ADR-0016)."""

from __future__ import annotations

import pytest

from caddcalc.gui.welcome_layout import Rect, Size, contain_fit, cover_crop, fit_scale, pane_rect
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
    assert small == pytest.approx(911 / window.width)
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
