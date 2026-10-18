"""The welcome screen, composed from a branding pack's parts (ADR-0015, ADR-0016).

A frameless card with a thin border and rounded outer corners: a top bar with an About
button (ⓘ) and an X, over the art. The logo sits in a box floating over the art's left
edge, and the name and version sit over the art in quiet panes. The app's menus live in
the main window (ADR-0015, amendments). The art and the logo come from the pack, or are
generated (``welcome_art``). Every size, colour role, and font comes from the design
tokens (``welcome_style``), placed by ``welcome_layout``; a test keeps literals out of
here.

Lines are whole device pixels on device-pixel centres, and only the card's rounded
outline is antialiased, so the card stays crisp at 125% and 150% scaling (ADR-0016,
amendments).
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import override

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QImage,
    QImageReader,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QResizeEvent,
    QScreen,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from caddcalc import __version__
from caddcalc.gui.actions import AppActions
from caddcalc.gui.branding import GENERIC_ICON, PRODUCT_NAME, Branding
from caddcalc.gui.fonts import display_family
from caddcalc.gui.icons import Scheme, current_scheme, icon, role_color
from caddcalc.gui.painting import on_device_pixels, stroke
from caddcalc.gui.welcome_art import generic_art
from caddcalc.gui.welcome_layout import (
    Rect,
    Size,
    contain_fit,
    cover_crop,
    device_line,
    device_rect,
    display_pixels,
    fit_scale,
    logo_box,
    pane_rect,
    scaled,
)
from caddcalc.gui.welcome_style import (
    RGB,
    PaneTokens,
    TypographyTokens,
    WelcomeStyle,
    every_pixel,
    opaque_fill,
    pane_fill,
    pane_pairs,
    style,
)

COMPOSITING_PLATFORMS = ("windows", "cocoa", "wayland", "offscreen")
"""Qt platforms whose windows are always composited, so a translucent card's rounded
corners show cleanly. Elsewhere the card keeps square corners (ADR-0016 §4, KI-020)."""


def read_image(path: Path | None, what: str) -> QImage | None:
    """Return the image at ``path``, or ``None`` with a warning if it can't be used.

    Its pixel size is read from the file's header and checked before the image is decoded,
    so an oversized file costs nothing (ADR-0015, amendments). Startup never fails because
    of art: the caller falls back to generated art.
    """
    if path is None:
        return None
    limit = style().art.max_px
    reader = QImageReader(str(path))
    size = reader.size()
    if not reader.canRead() or not size.isValid():
        warnings.warn(f"Ignoring the {what} {path.name}: it can't be read", stacklevel=2)
        return None
    if max(size.width(), size.height()) > limit:
        warnings.warn(
            f"Ignoring the {what} {path.name}: {size.width()} × {size.height()} px is larger "
            f"than {limit} px",
            stacklevel=2,
        )
        return None
    image = reader.read()
    if image.isNull():
        warnings.warn(f"Ignoring the {what} {path.name}: {reader.errorString()}", stacklevel=2)
        return None
    return image


def display_font(pixels: int, typography: TypographyTokens | None = None) -> QFont:
    """Return the display face, ``pixels`` pixels to the em, with its fallbacks.

    It's antialiased and unhinted, so a pixel face stays on its grid. Its weight is the
    token's: regular, or Qt's bold, which each platform's text engine draws differently
    (ADR-0016, amendments).
    """
    display_family()  # loads the vendored face on first use
    typography = style().typography if typography is None else typography
    font = QFont()
    font.setFamilies([typography.display_family, *typography.fallback_families])
    font.setPixelSize(pixels)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    bold = typography.display_weight == "bold"
    font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
    return font


def body_font(pixels: int) -> QFont:
    """Return the system's UI font, ``pixels`` pixels to the em."""
    font = QFont(QApplication.font())
    font.setPixelSize(pixels)
    return font


def can_round_corners() -> bool:
    """Return whether the card's corners can be rounded: its windowing system composites.

    Without a compositor, a translucent window's corners show black, so the card keeps
    square corners. Qt doesn't say whether an X11 desktop runs a compositor, so X11 keeps
    them square too (KI-020).
    """
    platform = QGuiApplication.platformName()
    return (
        platform.startswith(COMPOSITING_PLATFORMS) and QGuiApplication.primaryScreen() is not None
    )


def card_outline(p: QPainter, rect: QRectF, radius: float, border: float) -> QPainterPath:
    """Return the card's one rounded outline, along its border's centre line.

    The card clips its top bar and its art to this path, and strokes its border along it
    last, so the border covers the clip's edge and nothing shows outside the corners
    (ADR-0016, amendments). ``rect`` is the card, in the painter's coordinates.
    """
    ratio = p.deviceTransform().m11()
    half = device_line(border, ratio) / 2
    path = QPainterPath()
    inner = max(radius - half / ratio, 0)
    path.addRoundedRect(on_device_pixels(p, rect, half), inner, inner)
    return path


def card_background(scheme: Scheme) -> QColor:
    """Return the colour the card paints behind its top bar and its art.

    Art with transparent pixels shows it through, so the panes measure the art over it
    too, and what they measure is what the screen shows.
    """
    return QColor(role_color("background", scheme))


def _qrect(rect: Rect) -> QRectF:
    return QRectF(rect.x, rect.y, rect.width, rect.height)


class _TopBar(QWidget):
    """The bar across the top: the About button, the X, and a handle to drag the card by."""

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        handle = self.window().windowHandle()
        if event.button() is Qt.MouseButton.LeftButton and handle is not None:
            # The system moves the window, so dragging works on Wayland too (ADR-0015 W2).
            handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)


class _LogoBox(QWidget):
    """The logo's box, floating over the art's left edge: a fill, the logo, and a border.

    The box takes the logo's shape, as large as the logo area allows, centred, with a
    least short side and a greatest long side (ADR-0016 §3). The logo is contained in
    its padding. Without a logo, the box holds the app icon alone, so it's square.
    """

    def __init__(self, branding: Branding, parent: QWidget) -> None:
        super().__init__(parent)
        self._svg: QSvgRenderer | None = None
        self._image: QImage | None = None
        logo = branding.welcome_logo
        if logo is not None and logo.suffix.lower() == ".svg":
            renderer = QSvgRenderer(str(logo), self)
            if renderer.isValid():
                self._svg = renderer
            else:
                warnings.warn(f"Ignoring the welcome logo {logo.name}: invalid SVG", stacklevel=2)
        elif logo is not None:
            self._image = read_image(logo, "welcome logo")
        self.source = "pack" if self._svg is not None or self._image is not None else "generic"
        """Where the logo came from: ``"pack"``, or ``"generic"``."""
        if self.source == "generic":
            # The generic mark is the app icon alone; the name is in the title pane.
            self._image = read_image(GENERIC_ICON, "app icon")
        self.scale = 1.0
        """The card's scale, set by the screen, so the padding and border shrink with it."""
        self.tokens = branding.welcome_tokens
        self.setAccessibleName(f"{PRODUCT_NAME} logo")

    @property
    def logo_size(self) -> Size:
        """The logo's own size; a square when there's nothing to draw."""
        if self._svg is not None:
            size = self._svg.defaultSize()
            return Size(size.width(), size.height())
        if self._image is not None:
            ratio = self._image.devicePixelRatio()
            return Size(self._image.width() / ratio, self._image.height() / ratio)
        return Size(1, 1)

    def place(self, scale: float) -> None:
        """Size the box around the logo, inside the logo area, at the card's ``scale``."""
        logo = self.tokens.logo
        self.scale = scale
        area = scaled(self.tokens.logo_area, scale)
        least, most = logo.min_short_side * scale, logo.max_long_side * scale
        box = logo_box(self.logo_size, area, logo.padding * scale, least, most)
        self.setGeometry(round(box.x), round(box.y), round(box.width), round(box.height))

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens, scheme = self.tokens.logo, current_scheme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(role_color(tokens.fill_role, scheme)))
        inner = tokens.padding * self.scale
        area = Rect(inner, inner, self.width() - 2 * inner, self.height() - 2 * inner)
        target = _qrect(contain_fit(self.logo_size, area))
        if self._svg is not None:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)  # the logo's own shapes
            self._svg.render(p, target)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        elif self._image is not None:
            p.drawImage(target, self._image)
        border = QColor(role_color(tokens.border_role, scheme))
        stroke(p, QRectF(self.rect()), border, tokens.border_width * self.scale)
        p.end()


class _Pane(QWidget):
    """A quiet pane over the art: text in a translucent fill and a thin border (ADR-0016 §5).

    It hugs its text and sits at its anchor corner. Each text role has its own fill, dark
    text on a light fill and light text on a dark one; the fill starts at the minimum
    opacity and rises only as far as its text needs to reach the pane's contrast over all
    but a small share of the art beneath, every pixel under it, at the display's
    resolution, blended as the screen blends it, and the background to be calm enough
    not to break the letters up. The pair that needs the least wins.

    The display face is drawn at a whole multiple of its pixel grid, and centred on its
    capitals: the padding is the space around the caps (ADR-0016, amendments). The text
    is drawn in device pixels, so its size and baseline land on the display's grid, and
    as its outline in both panes; the text stays the pane's accessible name.
    """

    def __init__(self, text: str, tokens: WelcomeStyle, pane: PaneTokens, parent: QWidget) -> None:
        super().__init__(parent)
        self.panes = tokens.panes
        """The style the panes share."""
        self.typography = tokens.typography
        self.tokens = pane
        """Where this pane sits, its text, and its contrast."""
        self.text = text
        self.scale = 1.0
        self.art: list[RGB] | None = None
        """The art's colours under the pane, every device pixel, once measured."""
        self.text_font = QFont()
        """The font its text is drawn in, at its size in device pixels."""
        self._run = (0.0, 0.0, 0.0)  # the text's width, band height, and baseline, in device px
        self._outline = QPainterPath()  # the text, drawn as its outline
        self._ratio = 1.0
        self._fills: dict[Scheme, tuple[str, str, int]] = {}
        self.setAccessibleName(text)

    def fill(self, scheme: Scheme) -> tuple[str, str, int]:
        """Return the text's role, its fill's role, and the fill's alpha, 0 to 255.

        Until the art is measured, the fill is opaque.
        """
        if scheme not in self._fills:
            pairs = pane_pairs(self.panes, scheme)
            if self.art is None:
                index, alpha = opaque_fill(pairs)
            else:
                index, alpha = pane_fill(self.art, pairs, self.panes, self.tokens.min_contrast)
            self._fills[scheme] = self.panes.text_roles[index], self.panes.fill_roles[index], alpha
        return self._fills[scheme]

    def font_at(self, scale: float, ratio: float) -> QFont:
        """Return the pane's font, sized in device pixels, at the card's ``scale``."""
        typography = self.typography
        if self.tokens.font == "display":
            grid = display_pixels(self.tokens.font_size, scale, ratio, typography.display_em_pixels)
            return display_font(grid * typography.display_em_pixels, typography)
        size = max(typography.min_font_size, self.tokens.font_size * scale)
        return body_font(round(size * ratio))

    def place(self, slot: Size, scale: float) -> None:
        """Size the pane around its text and put it at its anchor corner of ``slot``."""
        ratio = self.devicePixelRatioF()
        font = self.font_at(scale, ratio)
        metrics = QFontMetricsF(font)  # the font as drawn, bold included
        width = metrics.horizontalAdvance(self.text)
        self._outline = QPainterPath()
        self._outline.addText(QPointF(0, 0), font, self.text)
        width = max(width, self._outline.boundingRect().right())
        if self.tokens.font == "display":
            band = self.typography.display_cap_height * font.pixelSize()
            run = (width, band, band)  # centred on the capitals
        else:
            run = (width, metrics.height(), metrics.ascent())  # centred on the line
        vertical, horizontal = (side * scale for side in self.tokens.padding)
        size = Size(
            math.ceil(width / ratio + 2 * horizontal), math.ceil(run[1] / ratio + 2 * vertical)
        )
        rect = pane_rect(self.tokens.anchor, self.tokens.inset * scale, size, slot)
        self.setGeometry(round(rect.x), round(rect.y), int(size.width), int(size.height))
        self.scale, self._ratio, self._run, self.text_font = scale, ratio, run, font

    def measure(self, art: QImage) -> None:
        """Measure every pixel of the art under the pane, from ``art`` as the slot shows it.

        ``art`` is drawn at the display's device pixel ratio, so detail finer than a
        logical pixel is measured as the screen shows it, not averaged away.
        """
        box = self.geometry()
        logical = Rect(box.x(), box.y(), box.width(), box.height())
        device = device_rect(logical, art.devicePixelRatio())
        rect = QRect(round(device.x), round(device.y), round(device.width), round(device.height))
        under = art.copy(rect.intersected(art.rect()))
        under = under.convertToFormat(QImage.Format.Format_RGBX8888)
        pixels = bytes(under.constBits())  # under stays alive while its pixels are read
        self.art = every_pixel(pixels, under.width(), under.height())
        self._fills.clear()
        self.fill(current_scheme())  # now, so the card's first paint doesn't wait on it
        self.update()

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        scheme = current_scheme()
        text_role, fill_role, alpha = self.fill(scheme)
        text = QColor(role_color(text_role, scheme))
        fill = QColor(role_color(fill_role, scheme))
        fill.setAlpha(alpha)
        p = QPainter(self)
        p.fillRect(self.rect(), fill)
        stroke(p, QRectF(self.rect()), text, self.panes.border_width * self.scale)  # follows text
        width, band, baseline = self._run
        p.scale(1 / self._ratio, 1 / self._ratio)  # device pixels from here on
        origin = p.deviceTransform()
        x = (self.width() * self._ratio - width) / 2
        y = (self.height() * self._ratio - band) / 2 + baseline
        at = QPointF(round(origin.dx() + x) - origin.dx(), round(origin.dy() + y) - origin.dy())
        # The text is filled as its outline: grey antialiasing on every platform, where
        # some text engines would add a colour fringe, and both panes alike.
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillPath(self._outline.translated(at), text)
        p.end()


class _ArtSlot(QWidget):
    """The art, covering the card's width around its focal point, with what floats over it.

    The logo box sits over its left edge, and the name and version panes at their corners.
    """

    def __init__(self, branding: Branding, parent: QWidget) -> None:
        super().__init__(parent)
        self._art = read_image(branding.welcome_art, "welcome art")
        self._focus = branding.welcome_focus
        self._generic: QImage | None = None
        self.source = "generic" if self._art is None else "pack"
        """Where the art came from: ``"pack"``, or ``"generic"`` when there was none or it
        couldn't be used."""
        tokens = branding.welcome_tokens
        self.slot = tokens.art.slot
        self.radius = 0.0
        """The card's corner radius, which rounds the art's lower corners."""
        self.border = 0.0
        """The card's border width, whose centre line the art is clipped to."""
        self.placed = False
        """Whether the logo box and the panes have been placed, once the slot has its size."""
        self.logo = _LogoBox(branding, self)
        self.name_pane = _Pane(PRODUCT_NAME, tokens, tokens.name_pane, self)
        version = f"Version {__version__}"
        self.version_pane = _Pane(version, tokens, tokens.version_pane, self)

    def shown_art(self) -> QImage:
        """Return the art as the slot shows it, one image pixel per device pixel.

        The image starts as the card's background, which shows through transparent art.
        """
        ratio = self.devicePixelRatioF()
        size = QSize(math.ceil(self.width() * ratio), math.ceil(self.height() * ratio))
        image = QImage(size, QImage.Format.Format_RGBX8888)
        image.setDevicePixelRatio(ratio)
        image.fill(card_background(current_scheme()))
        p = QPainter(image)
        self._draw(p)
        p.end()
        return image

    def _draw(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        ratio = self.devicePixelRatioF()
        if self._art is not None:
            image = self._art
        else:
            if self._generic is None or self._generic.devicePixelRatio() != ratio:
                self._generic = generic_art(self.size(), ratio)
            image = self._generic
        target = QRectF(self.rect())
        r = image.devicePixelRatio()
        width, height = image.width() / r, image.height() / r
        crop = cover_crop(Size(width, height), Size(target.width(), target.height()), self._focus)
        p.drawImage(target, image, QRectF(crop.x * r, crop.y * r, crop.width * r, crop.height * r))

    def _place(self) -> None:
        """Place the logo box and the panes, and measure the art under the panes."""
        scale = self.width() / self.slot.width
        slot = Size(self.width(), self.height())
        self._generic = None
        self.logo.place(scale)
        for pane in (self.name_pane, self.version_pane):
            pane.place(slot, scale)
        self.placed = True
        self.measure()

    def measure(self) -> None:
        """Measure the art under each pane, as the slot shows it over the card."""
        art = self.shown_art()
        for pane in (self.name_pane, self.version_pane):
            pane.measure(art)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        self._place()
        super().resizeEvent(event)

    @override
    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.DevicePixelRatioChange:
            self._place()  # the text snaps to the new display's grid
        super().changeEvent(event)

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        card = self.parentWidget()
        if card is not None:
            outline = QRectF(card.rect()).translated(-self.x(), -self.y())
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setClipPath(card_outline(p, outline, self.radius, self.border))
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._draw(p)
        p.end()


class _Border(QWidget):
    """The card's frame, over everything else: the separator, then the rounded border.

    It takes no mouse events, so the top bar and buttons beneath it work. The border is
    stroked last, along the outline the card and the art are clipped to (ADR-0016 §4).
    """

    def __init__(self, tokens: WelcomeStyle, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tokens = tokens
        self.radius = 0.0
        """The outer corners' radius; 0 for square corners."""
        self.scale = 1.0
        """The card's scale, so the lines shrink with it."""
        self.bar_height = 0
        """The top bar's height in whole pixels, so the separator under it stays crisp."""

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens, scheme = self.tokens, current_scheme()
        p = QPainter(self)
        ratio = p.deviceTransform().m11()
        border = tokens.card.border_width * self.scale
        edge = device_line(border, ratio) / ratio
        separator = device_line(tokens.top_bar.separator_width * self.scale, ratio) / ratio
        if separator:
            bar = on_device_pixels(p, QRectF(0, 0, self.width(), self.bar_height))
            p.fillRect(
                QRectF(
                    bar.left() + edge, bar.bottom() - separator, bar.width() - 2 * edge, separator
                ),
                QColor(role_color(tokens.top_bar.separator_role, scheme)),
            )
        if edge:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)  # the one antialiased path
            outline = card_outline(p, QRectF(self.rect()), self.radius, border)
            p.strokePath(outline, QPen(QColor(role_color(tokens.card.border_role, scheme)), edge))
        p.end()


class WelcomeScreen(QWidget):
    """The welcome screen: art, logo, name, and version, with an About button and an X.

    It is application-modal, so it blocks the main window until it's closed (ADR-0015 W5,
    amendments). Esc or the X closes it, and it's deleted when closed. Connections use
    bound methods only (KI-019).

    Attributes:
        painted: Emitted once, when the card first paints: it's on screen.
        closed: Emitted when the card closes.
    """

    painted = Signal()
    closed = Signal()

    def __init__(
        self, branding: Branding, actions: AppActions, parent: QWidget | None = None
    ) -> None:
        """Compose the screen for ``branding``; its About button triggers ``actions.about``."""
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._painted = False
        self.setWindowTitle(PRODUCT_NAME)
        self.setAccessibleName(f"Welcome to {PRODUCT_NAME}")
        tokens = branding.welcome_tokens
        self.display_face = display_family()
        """The display face its text uses: the tokens' family, or ``"fallback"``."""
        self.rounded = can_round_corners()
        """Whether its corners are rounded; they're square without a compositor (KI-020)."""
        if self.rounded:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        scale = self._fit_scale()
        window = tokens.window
        self.setFixedSize(round(window.width * scale), round(window.height * scale))
        self._centre()

        self.top_bar = _TopBar(self)
        self.top_bar.setFixedHeight(round(tokens.top_bar.height * scale))
        button = round(tokens.top_bar.button_size * scale)
        self.about_button = QToolButton(self.top_bar)
        self.about_button.setAutoRaise(True)
        self.about_button.setFixedSize(button, button)
        self.about_button.setToolTip(f"About {PRODUCT_NAME}: version, license, and terms")
        self.about_button.setAccessibleName("About")
        self.about_button.clicked.connect(actions.about.trigger)
        self.app_actions = actions
        """The commands its About button triggers; kept, so they live as long as it does."""
        self.close_button = QToolButton(self.top_bar)
        self.close_button.setAutoRaise(True)
        self.close_button.setFixedSize(button, button)
        self.close_button.setToolTip("Close (Esc)")
        self.close_button.setAccessibleName("Close")
        self.close_button.clicked.connect(self.close)
        padding = round(tokens.top_bar.padding * scale)
        bar = QHBoxLayout(self.top_bar)
        bar.setContentsMargins(padding, 0, padding, 0)
        bar.addStretch(1)
        bar.addWidget(self.about_button)
        bar.addWidget(self.close_button)

        self.art = _ArtSlot(branding, self)
        slot = tokens.art.slot
        self.art.setFixedSize(round(slot.width * scale), round(slot.height * scale))
        self.logo = self.art.logo
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.top_bar)
        column.addWidget(self.art)

        self.radius = tokens.card.corner_radius * scale if self.rounded else 0
        """The outer corners' radius: the token's, shrunk with the card; 0 when square."""
        self.border_width = tokens.card.border_width * scale
        self.art.radius, self.art.border = self.radius, self.border_width
        self.border = _Border(tokens, self)
        self.border.scale = scale
        self.border.radius = self.radius
        self.border.bar_height = self.top_bar.height()
        self.border.setGeometry(self.rect())
        self.border.raise_()

        self._apply_theme()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

    @property
    def art_source(self) -> str:
        """Where the art came from: ``"pack"``, or ``"generic"``."""
        return self.art.source

    @property
    def logo_source(self) -> str:
        """Where the logo came from: ``"pack"``, or ``"generic"``."""
        return self.logo.source

    def _fit_scale(self) -> float:
        """Return the scale that fits the card on its screen, at most 1 (ADR-0015)."""
        screen = self._card_screen()
        if screen is None:
            return 1.0
        available = screen.availableGeometry()
        return fit_scale(Size(available.width(), available.height()))

    def _card_screen(self) -> QScreen | None:
        """Return the screen the card shows on: its window's, its own, or the primary."""
        return (self.parentWidget() or self).screen() or QGuiApplication.primaryScreen()

    def _centre(self) -> None:
        """Centre the card in its screen's work area, where the main window opens too.

        A frameless window's place is otherwise the system's, which may cascade it into a
        corner away from the main window (ADR-0021 §3).
        """
        screen = self._card_screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.x() + (area.width() - self.width()) // 2
        y = area.y() + (area.height() - self.height()) // 2
        self.move(x, y)

    def _apply_theme(self) -> None:
        scheme = current_scheme()
        self.about_button.setIcon(icon("info-circle", "icon_active", scheme))
        self.close_button.setIcon(icon("x", "icon_active", scheme))
        if self.art.placed:  # transparent art now shows another background
            self.art.measure()
        self.update()

    def _on_color_scheme_changed(self, *_args: object) -> None:
        self._apply_theme()

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline = card_outline(p, QRectF(self.rect()), self.radius, self.border_width)
        p.fillPath(outline, card_background(current_scheme()))
        p.end()
        if not self._painted:
            self._painted = True
            self.painted.emit()

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        if event.isAccepted():
            self.closed.emit()

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    @override
    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.PaletteChange:
            self._apply_theme()
        super().changeEvent(event)
