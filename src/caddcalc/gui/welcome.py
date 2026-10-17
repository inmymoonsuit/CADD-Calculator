"""The welcome screen, composed from a branding pack's parts (ADR-0015, ADR-0016).

A frameless card with a thin border and rounded outer corners: a top bar with an About
button (ⓘ) and an X, over the art. The logo sits in a box floating over the art's left
edge, and the name and version sit over the art in quiet panes. The app's menus live in
the main window (ADR-0015, amendments). The art and the logo come from the pack, or are
generated (``welcome_art``). Every size, colour role, and font comes from the design
tokens (``welcome_style``), placed by ``welcome_layout``; a test keeps literals out of
here.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import override

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import (
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
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from caddcalc import __version__
from caddcalc.gui.actions import AppActions
from caddcalc.gui.branding import GENERIC_ICON, PRODUCT_NAME, Branding
from caddcalc.gui.fonts import display_family
from caddcalc.gui.icons import Scheme, current_scheme, icon, role_color
from caddcalc.gui.welcome_art import generic_art, generic_logo
from caddcalc.gui.welcome_layout import (
    Rect,
    Size,
    contain_fit,
    cover_crop,
    fit_scale,
    logo_box,
    pane_rect,
    scaled,
)
from caddcalc.gui.welcome_style import (
    RGB,
    PaneTokens,
    opaque_fill,
    pane_fill,
    percentile_colors,
    rgb,
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


def line_width(width: float, widget: QWidget) -> float:
    """Return a line's width in logical pixels: ``width``, but never under one device pixel."""
    return max(width, 1 / widget.devicePixelRatioF()) if width else width


def display_font(pixel_size: float) -> QFont:
    """Return the display face at ``pixel_size``, at its token weight, with its fallbacks.

    VT323 has only a regular file, so its bold (S1) is the one Qt synthesizes.
    """
    display_family()  # loads the vendored face on first use
    typography = style().typography
    font = QFont()
    font.setFamilies([typography.display_family, *typography.fallback_families])
    font.setWeight(QFont.Weight(typography.display_weight))
    font.setPixelSize(max(round(typography.min_font_size), round(pixel_size)))
    return font


def body_font(pixel_size: float) -> QFont:
    """Return the system's UI font at ``pixel_size``."""
    font = QFont(QApplication.font())
    font.setPixelSize(max(round(style().typography.min_font_size), round(pixel_size)))
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


def _outline(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def _stroke(p: QPainter, rect: QRectF, color: QColor, width: float, radius: float = 0) -> None:
    """Draw a line ``width`` wide just inside ``rect``, with corners of ``radius``."""
    half = width / 2
    p.setPen(QPen(color, width))
    p.setBrush(Qt.BrushStyle.NoBrush)
    inner = max(radius - half, 0)
    p.drawRoundedRect(rect.adjusted(half, half, -half, -half), inner, inner)


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

    The box takes the logo's shape, as large as the logo area allows, centred, and never
    smaller than its minimum (ADR-0016 §3). The logo is contained in its padding.
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
        self.scale = 1.0
        """The card's scale, set by the screen, so the padding and border shrink with it."""
        self.setAccessibleName(f"{PRODUCT_NAME} logo")

    @property
    def logo_size(self) -> Size | None:
        """The logo's own size; ``None`` for the generic logo, which fills its box."""
        if self._svg is not None:
            size = self._svg.defaultSize()
            return Size(size.width(), size.height())
        if self._image is not None:
            ratio = self._image.devicePixelRatio()
            return Size(self._image.width() / ratio, self._image.height() / ratio)
        return None

    def place(self, scale: float) -> None:
        """Size the box around the logo, inside the logo area, at the card's ``scale``."""
        tokens = style()
        self.scale = scale
        minimum = Size(tokens.logo.min_size.width * scale, tokens.logo.min_size.height * scale)
        area = scaled(tokens.logo_area, scale)
        box = logo_box(self.logo_size, area, tokens.logo.padding * scale, minimum)
        self.setGeometry(round(box.x), round(box.y), round(box.width), round(box.height))

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens, scheme = style().logo, current_scheme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(role_color(tokens.fill_role, scheme)))
        inner = tokens.padding * self.scale
        area = Rect(inner, inner, self.width() - 2 * inner, self.height() - 2 * inner)
        size = self.logo_size
        if self._svg is not None and size is not None:
            self._svg.render(p, _qrect(contain_fit(size, area)))
        elif self._image is not None and size is not None:
            p.drawImage(_qrect(contain_fit(size, area)), self._image)
        else:
            logo = generic_logo(
                QSize(round(area.width), round(area.height)),
                self.devicePixelRatioF(),
                GENERIC_ICON,
                PRODUCT_NAME,
                role_color("text", scheme),
            )
            p.drawImage(_qrect(area), logo)
        width = line_width(tokens.border_width * self.scale, self)
        if width:
            _stroke(p, QRectF(self.rect()), QColor(role_color(tokens.border_role, scheme)), width)
        p.end()


class _Pane(QWidget):
    """A quiet pane over the art: text in a translucent fill and a thin border (ADR-0016 §5).

    It hugs its text and sits at its anchor corner. Its fill starts at the minimum opacity
    and rises only as far as the text needs to read against the art beneath, measured at
    the art's luminance percentiles; the text takes the role that needs the least.
    """

    def __init__(self, text: str, tokens: PaneTokens, parent: QWidget) -> None:
        super().__init__(parent)
        self.tokens = tokens
        self.text = text
        self.scale = 1.0
        self.art: tuple[RGB, RGB] | None = None
        """The art's colours under the pane, at its luminance percentiles, once measured."""
        self._fills: dict[Scheme, tuple[str, int]] = {}
        self.setAccessibleName(text)

    def fill(self, scheme: Scheme) -> tuple[str, int]:
        """Return the text's role and the fill's alpha, 0 to 255, over the art beneath.

        Until the art is measured, the fill is opaque.
        """
        if scheme not in self._fills:
            panes = style().panes
            fill = rgb(role_color(panes.fill_role, scheme))
            texts = [rgb(role_color(role, scheme)) for role in panes.text_roles]
            if self.art is None:
                index, alpha = opaque_fill(fill, texts)
            else:
                index, alpha = pane_fill(self.art, fill, texts, panes)
            self._fills[scheme] = panes.text_roles[index], alpha
        return self._fills[scheme]

    def font_at(self, scale: float) -> QFont:
        """Return the pane's font at the card's ``scale``."""
        size = self.tokens.font_size * scale
        return display_font(size) if self.tokens.font == "display" else body_font(size)

    def place(self, slot: Size, scale: float) -> None:
        """Size the pane around its text and put it at its anchor corner of ``slot``."""
        self.scale = scale
        self.setFont(self.font_at(scale))
        metrics = QFontMetricsF(self.font())
        vertical, horizontal = (side * scale for side in self.tokens.padding)
        size = Size(
            metrics.horizontalAdvance(self.text) + 2 * horizontal,
            metrics.height() + 2 * vertical,
        )
        rect = pane_rect(self.tokens.anchor, self.tokens.inset * scale, size, slot)
        self.setGeometry(round(rect.x), round(rect.y), round(rect.width), round(rect.height))

    def measure(self, art: QImage) -> None:
        """Measure the art under the pane, from ``art`` as the slot shows it."""
        under = art.copy(self.geometry()).convertToFormat(QImage.Format.Format_RGBX8888)
        self.art = percentile_colors(bytes(under.constBits()), style().panes.percentiles)
        self._fills.clear()
        self.update()

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        panes, scheme = style().panes, current_scheme()
        role, alpha = self.fill(scheme)
        text = QColor(role_color(role, scheme))
        fill = QColor(role_color(panes.fill_role, scheme))
        fill.setAlpha(alpha)
        p = QPainter(self)
        p.fillRect(self.rect(), fill)
        width = line_width(panes.border_width * self.scale, self)
        if width:
            _stroke(p, QRectF(self.rect()), text, width)  # the border follows the text
        p.setPen(text)
        p.setFont(self.font())
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, self.text)
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
        tokens = style()
        self.logo = _LogoBox(branding, self)
        self.name_pane = _Pane(PRODUCT_NAME, tokens.name_pane, self)
        self.version_pane = _Pane(f"Version {__version__}", tokens.version_pane, self)

    def shown_art(self) -> QImage:
        """Return the art as the slot shows it, one image pixel per logical pixel."""
        image = QImage(self.size(), QImage.Format.Format_RGBX8888)
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

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        scale = self.width() / style().art.slot.width
        slot = Size(self.width(), self.height())
        self._generic = None
        self.logo.place(scale)
        art = self.shown_art()
        for pane in (self.name_pane, self.version_pane):
            pane.place(slot, scale)
            pane.measure(art)
        super().resizeEvent(event)

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        self._draw(p)
        p.end()


class _Border(QWidget):
    """The card's frame, over everything else: its rounded corners, border, and separator.

    It takes no mouse events, so the top bar and buttons beneath it work. Outside the
    rounded outline it clears what the card and the art drew, so the corners show the
    desktop through the translucent window (ADR-0016 §4).
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.radius = 0.0
        """The outer corners' radius; 0 for square corners."""
        self.scale = 1.0
        """The card's scale, so the lines shrink with it."""
        self.bar_height = 0
        """The top bar's height in whole pixels, so the separator under it stays crisp."""

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens, scheme = style(), current_scheme()
        rect = QRectF(self.rect())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.radius:
            outside = QPainterPath()
            outside.addRect(rect)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillPath(outside.subtracted(_outline(rect, self.radius)), QColor())
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        border = line_width(tokens.card.border_width * self.scale, self)
        separator = line_width(tokens.top_bar.separator_width * self.scale, self)
        if separator:
            bottom = self.bar_height
            p.fillRect(
                QRectF(border, bottom - separator, rect.width() - 2 * border, separator),
                QColor(role_color(tokens.top_bar.separator_role, scheme)),
            )
        if border:
            color = QColor(role_color(tokens.card.border_role, scheme))
            _stroke(p, rect, color, border, self.radius)
        p.end()


class WelcomeScreen(QWidget):
    """The welcome screen: art, logo, name, and version, with an About button and an X.

    It is application-modal, so it blocks the main window until it's closed (ADR-0015 W5,
    amendments). Esc or the X closes it, and it's deleted when closed. Connections use
    bound methods only (KI-019).
    """

    def __init__(
        self, branding: Branding, actions: AppActions, parent: QWidget | None = None
    ) -> None:
        """Compose the screen for ``branding``; its About button triggers ``actions.about``."""
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(PRODUCT_NAME)
        self.setAccessibleName(f"Welcome to {PRODUCT_NAME}")
        tokens = style()
        self.display_face = display_family()
        """The display face its text uses: the tokens' family, or ``"fallback"``."""
        self.rounded = can_round_corners()
        """Whether its corners are rounded; they're square without a compositor (KI-020)."""
        if self.rounded:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        scale = self._fit_scale()
        window = tokens.window
        self.setFixedSize(round(window.width * scale), round(window.height * scale))

        self.top_bar = _TopBar(self)
        self.top_bar.setFixedHeight(round(tokens.top_bar.height * scale))
        self.about_button = QToolButton(self.top_bar)
        self.about_button.setAutoRaise(True)
        self.about_button.setToolTip(f"About {PRODUCT_NAME}: version, license, and terms")
        self.about_button.setAccessibleName("About")
        self.about_button.clicked.connect(actions.about.trigger)
        self.app_actions = actions
        """The commands its About button triggers; kept, so they live as long as it does."""
        self.close_button = QToolButton(self.top_bar)
        self.close_button.setAutoRaise(True)
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

        self.border = _Border(self)
        self.border.scale = scale
        self.border.bar_height = self.top_bar.height()
        self.border.radius = tokens.card.corner_radius * self.height() if self.rounded else 0
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
        screen = (self.parentWidget() or self).screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return 1.0
        available = screen.availableGeometry()
        return fit_scale(Size(available.width(), available.height()))

    def _apply_theme(self) -> None:
        scheme = current_scheme()
        self.about_button.setIcon(icon("info-circle", "icon_active", scheme))
        self.close_button.setIcon(icon("x", "icon_active", scheme))
        self.update()

    def _on_color_scheme_changed(self, *_args: object) -> None:
        self._apply_theme()

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(role_color("background", current_scheme())))
        p.end()

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
