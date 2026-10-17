"""The welcome screen, composed from a branding pack's parts (ADR-0015, ADR-0016).

A frameless card: a top bar with an About button (ⓘ) and an X, a logo region, and an
art slot with the name and version over it, in panes. The app's menus live in the main
window (ADR-0015, amendments). The art and the logo come from the pack, or are generated
(``welcome_art``). Every size, colour role, and font comes from the design tokens
(``welcome_style``), placed by ``welcome_layout``; a test keeps literals out of here.
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
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from caddcalc import __version__
from caddcalc.gui.actions import AppActions
from caddcalc.gui.branding import GENERIC_ICON, Branding
from caddcalc.gui.fonts import display_family
from caddcalc.gui.icons import Scheme, current_scheme, icon, role_color
from caddcalc.gui.welcome_art import generic_art, generic_logo
from caddcalc.gui.welcome_layout import Rect, Size, contain_fit, cover_crop, fit_scale, pane_rect
from caddcalc.gui.welcome_style import PaneTokens, contrast, luminance, style


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


class _LogoRegion(QWidget):
    """The logo region: the pack's logo, or the generic one, inside the box's padding."""

    def __init__(self, branding: Branding, parent: QWidget) -> None:
        super().__init__(parent)
        self._name = branding.name
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
        """The card's scale, set by the screen, so the padding shrinks with it."""
        self.setAccessibleName(f"{self._name} logo")

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens, scheme = style().logo, current_scheme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(role_color(tokens.fill_role, scheme)))
        inner = tokens.padding * self.scale
        area = Rect(inner, inner, self.width() - 2 * inner, self.height() - 2 * inner)
        if self._svg is not None:
            size = self._svg.defaultSize()
            self._svg.render(p, _qrect(contain_fit(Size(size.width(), size.height()), area)))
        elif self._image is not None:
            size = self._image.size()
            target = contain_fit(Size(size.width(), size.height()), area)
            p.drawImage(_qrect(target), self._image)
        else:
            logo = generic_logo(
                QSize(round(area.width), round(area.height)),
                self.devicePixelRatioF(),
                GENERIC_ICON,
                self._name,
                role_color("text", scheme),
            )
            p.drawImage(_qrect(area), logo)
        p.end()


def _qrect(rect: Rect) -> QRectF:
    return QRectF(rect.x, rect.y, rect.width, rect.height)


class _Pane(QWidget):
    """A quiet pane over the art: text in a fill and a thin border (ADR-0016 §5).

    It hugs its text and sits at its anchor corner. The text takes whichever of the two
    text roles contrasts more with the fill.
    """

    def __init__(self, text: str, tokens: PaneTokens, parent: QWidget) -> None:
        super().__init__(parent)
        self.tokens = tokens
        self.text = text
        self.scale = 1.0
        self.setAccessibleName(text)

    def text_role(self, scheme: Scheme) -> str:
        """Return the text role that contrasts more with the fill."""
        panes = style().panes
        fill = luminance(role_color(panes.fill_role, scheme))
        return max(
            panes.text_roles, key=lambda role: contrast(luminance(role_color(role, scheme)), fill)
        )

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

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        panes, scheme = style().panes, current_scheme()
        text = QColor(role_color(self.text_role(scheme), scheme))
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(role_color(panes.fill_role, scheme)))
        width = line_width(panes.border_width * self.scale, self)
        if width:
            p.setPen(QPen(text, width))
            half = width / 2
            p.drawRect(QRectF(self.rect()).adjusted(half, half, -half, -half))
        p.setPen(text)
        p.setFont(self.font())
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, self.text)
        p.end()


class _ArtSlot(QWidget):
    """The art, covering the slot around its focal point, with the name and version over it."""

    def __init__(self, branding: Branding, parent: QWidget) -> None:
        super().__init__(parent)
        self._art = read_image(branding.welcome_art, "welcome art")
        self._focus = branding.welcome_focus
        self._generic: QImage | None = None
        self.source = "generic" if self._art is None else "pack"
        """Where the art came from: ``"pack"``, or ``"generic"`` when there was none or it
        couldn't be used."""
        tokens = style()
        self.name_pane = _Pane(branding.name, tokens.name_pane, self)
        self.version_pane = _Pane(f"Version {__version__}", tokens.version_pane, self)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        scale = self.width() / style().art.slot.width
        slot = Size(self.width(), self.height())
        for pane in (self.name_pane, self.version_pane):
            pane.place(slot, scale)
        self._generic = None
        super().resizeEvent(event)

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        target = QRectF(self.rect())
        if self._art is not None:
            image = self._art
        else:
            ratio = self.devicePixelRatioF()
            if self._generic is None or self._generic.devicePixelRatio() != ratio:
                self._generic = generic_art(self.size(), ratio)
            image = self._generic
        r = image.devicePixelRatio()
        width, height = image.width() / r, image.height() / r
        crop = cover_crop(Size(width, height), Size(target.width(), target.height()), self._focus)
        p.drawImage(target, image, QRectF(crop.x * r, crop.y * r, crop.width * r, crop.height * r))
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
        self.setWindowTitle(branding.name)
        self.setAccessibleName(f"Welcome to {branding.name}")
        tokens = style()
        self.display_face = display_family()
        """The display face its text uses: the tokens' family, or ``"fallback"``."""

        scale = self._fit_scale()
        window = tokens.window
        self.setFixedSize(round(window.width * scale), round(window.height * scale))

        self.top_bar = _TopBar(self)
        self.top_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.top_bar.setFixedHeight(round(tokens.top_bar.height * scale))
        self.about_button = QToolButton(self.top_bar)
        self.about_button.setAutoRaise(True)
        self.about_button.setToolTip(f"About {branding.name}: version, license, and terms")
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

        self.logo = _LogoRegion(branding, self)
        self.logo.scale = scale
        self.logo.setFixedWidth(round(tokens.logo.region_width * scale))
        self.art = _ArtSlot(branding, self)
        slot = tokens.art.slot
        self.art.setFixedSize(round(slot.width * scale), round(slot.height * scale))
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.logo)
        body.addWidget(self.art)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.top_bar)
        column.addLayout(body)
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
        background, text = role_color("background", scheme), role_color("text", scheme)
        self.top_bar.setStyleSheet(f"background: {background}; color: {text};")
        self.about_button.setIcon(icon("info-circle", "icon_active", scheme))
        self.close_button.setIcon(icon("x", "icon_active", scheme))
        self.update()

    def _on_color_scheme_changed(self, *_args: object) -> None:
        self._apply_theme()

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
