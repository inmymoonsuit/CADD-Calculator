"""The welcome screen's geometry and art specification (ADR-0015 §3)."""

from __future__ import annotations

import pytest

from caddcalc.gui.welcome_layout import (
    ART_SIZE,
    ART_SUPPLIED,
    LOGO_STRIP,
    NAME_PANEL,
    TOP_BAR,
    VERSION_LINE,
    WINDOW,
    Rect,
    Size,
    cover_crop,
    fit_scale,
)


def test_the_sizes_add_up() -> None:
    assert ART_SIZE.width / ART_SIZE.height == 16 / 9
    assert Size(1920, 1080) == ART_SUPPLIED
    assert (LOGO_STRIP, TOP_BAR) == (72, 32)
    assert Size(1032, 572) == WINDOW


@pytest.mark.parametrize("area", [NAME_PANEL, VERSION_LINE])
def test_the_safe_areas_lie_inside_the_art_slot(area: Rect) -> None:
    assert area.x >= 0 and area.y >= 0
    assert area.x + area.width <= ART_SIZE.width
    assert area.y + area.height <= ART_SIZE.height


def test_art_of_the_slots_shape_is_shown_whole() -> None:
    assert cover_crop(Size(1920, 1080), ART_SIZE) == Rect(0, 0, 1920, 1080)


def test_wide_art_is_cropped_at_the_sides_around_its_focus() -> None:
    crop = cover_crop(Size(3200, 1080), ART_SIZE, (0.35, 0.5))
    assert (crop.width, crop.height, crop.y) == (1920, 1080, 0)
    assert crop.x == pytest.approx(0.35 * 3200 - 960)


def test_tall_art_is_cropped_top_and_bottom() -> None:
    crop = cover_crop(Size(1080, 1080), ART_SIZE)
    assert (crop.x, crop.width) == (0, 1080)
    assert crop.height == pytest.approx(607.5)
    assert crop.y == pytest.approx((1080 - 607.5) / 2)


@pytest.mark.parametrize(("focus", "x"), [((0.0, 0.5), 0.0), ((1.0, 0.5), 3200 - 1920)])
def test_a_focus_near_an_edge_keeps_the_crop_inside_the_art(
    focus: tuple[float, float], x: float
) -> None:
    assert cover_crop(Size(3200, 1080), ART_SIZE, focus).x == x


def test_the_screen_shrinks_to_fit_a_small_screen_and_never_grows() -> None:
    assert fit_scale(Size(1920, 1040)) == 1.0
    small = fit_scale(Size(911, 512))  # 1366 x 768 at 150%, less a taskbar
    assert small == pytest.approx(911 / 1032)
    assert WINDOW.width * small <= 911 and WINDOW.height * small <= 512
