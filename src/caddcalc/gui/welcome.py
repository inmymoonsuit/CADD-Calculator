"""The welcome screen, composed from a branding pack's parts (ADR-0015).

A frameless card: a top bar with an About button (ⓘ) and an X, a vertical logo strip,
and an art slot with the name and version as live text over it. The app's menus live in
the main window (ADR-0015, amendments). The art and the logo come from
the pack, or are drawn here from the palette. Everything is laid out from
``welcome_layout``, the art specification's one source.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import override

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QImageReader,
    QKeyEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from caddcalc import __version__
from caddcalc.gui.actions import AppActions
from caddcalc.gui.branding import GENERIC_ICON, Branding
from caddcalc.gui.icons import current_scheme, icon, palette, role_color
from caddcalc.gui.welcome_layout import (
    ART_SIZE,
    LOGO_STRIP,
    MAX_ART_PX,
    NAME_PANEL,
    TOP_BAR,
    VERSION_LINE,
    WINDOW,
    Rect,
    Size,
    cover_crop,
    fit_scale,
)


def read_image(path: Path | None, what: str) -> QImage | None:
    """Return the image at ``path``, or ``None`` with a warning if it can't be used.

    Its pixel size is read from the file's header and checked before the image is decoded,
    so an oversized file costs nothing (ADR-0015, amendments). Startup never fails because
    of art: the caller falls back to generated art.
    """
    if path is None:
        return None
    reader = QImageReader(str(path))
    size = reader.size()
    if not reader.canRead() or not size.isValid():
        warnings.warn(f"Ignoring the {what} {path.name}: it can't be read", stacklevel=2)
        return None
    if max(size.width(), size.height()) > MAX_ART_PX:
        warnings.warn(
            f"Ignoring the {what} {path.name}: {size.width()} × {size.height()} px is larger "
            f"than {MAX_ART_PX} px",
            stacklevel=2,
        )
        return None
    image = reader.read()
    if image.isNull():
        warnings.warn(f"Ignoring the {what} {path.name}: {reader.errorString()}", stacklevel=2)
        return None
    return image


def generic_art(size: QSize, device_pixel_ratio: float) -> QImage:
    """Return the public build's art, drawn from the palette at the screen's resolution.

    A flat pattern's bend lines over a slate field: original line work, so it needs no
    notice. It stands in until the roadmap's commissioned generic art exists.
    """
    width = max(1, round(size.width() * device_pixel_ratio))
    height = max(1, round(size.height() * device_pixel_ratio))
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(device_pixel_ratio)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = size.width(), size.height()
    gradient = QLinearGradient(QPointF(0, 0), QPointF(w, h))
    gradient.setColorAt(0, QColor(_color("ink")))
    gradient.setColorAt(1, QColor(_color("slate")))
    p.fillRect(QRectF(0, 0, w, h), gradient)
    unit = h / 9
    p.setPen(QPen(QColor(_color("amber")), max(1.0, unit / 30), Qt.PenStyle.DashLine))
    for i in range(1, 9):
        x = w * 0.08 + i * unit * 1.1
        p.drawLine(QPointF(x, h * 0.18), QPointF(x - unit * 1.6, h * 0.92))
    p.setPen(QPen(QColor(_color("crimson")), max(1.5, unit / 18)))
    p.drawArc(QRectF(w * 0.08, h * 0.30, unit * 7, unit * 7), 30 * 16, 120 * 16)
    p.end()
    return image


def _color(name: str) -> str:
    """A palette color by its name, such as ``"slate"``, for art that ignores the theme."""
    color: str = palette()["colors"][name]
    return color


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


class _LogoStrip(QWidget):
    """The vertical logo strip: the pack's logo, or the app icon and the name set upright."""

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
        self._icon = QImage(str(GENERIC_ICON))
        self.source = "pack" if self._svg is not None or self._image is not None else "generic"
        """Where the logo came from: ``"pack"``, or ``"generic"``."""
        self.setAccessibleName(f"{self._name} logo")

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scheme = current_scheme()
        p.fillRect(self.rect(), QColor(role_color("background", scheme)))
        area = QRectF(self.rect())
        if self._svg is not None:
            self._svg.render(p, _fit(self._svg.defaultSize(), area))
        elif self._image is not None:
            p.drawImage(_fit(self._image.size(), area), self._image)
        else:
            side = area.width() * 0.6
            p.drawImage(QRectF((area.width() - side) / 2, side * 0.3, side, side), self._icon)
            p.setPen(QColor(role_color("text", scheme)))
            font = QFont(self.font())
            font.setPixelSize(max(8, round(area.width() * 0.26)))
            font.setBold(True)
            p.setFont(font)
            p.translate(area.width() / 2, area.height() * 0.62)
            p.rotate(-90)
            text = QRectF(-area.height() / 2, -area.width() / 2, area.height(), area.width())
            p.drawText(text, Qt.AlignmentFlag.AlignCenter, self._name)
        p.end()


def _fit(source: QSize, area: QRectF) -> QRectF:
    """Return ``source`` scaled to fit inside ``area``, centred, keeping its shape."""
    if source.width() <= 0 or source.height() <= 0:
        return area
    scale = min(area.width() / source.width(), area.height() / source.height())
    w, h = source.width() * scale, source.height() * scale
    return QRectF(area.x() + (area.width() - w) / 2, area.y() + (area.height() - h) / 2, w, h)


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
        self.name_label = QLabel(branding.name, self)
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version = f"Version {__version__}"
        if not branding.is_generic:
            version += f" · {branding.edition}"
        self.version_label = QLabel(version, self)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.apply_theme()

    def apply_theme(self) -> None:
        """Colour the name panel and the version line for the current light or dark theme."""
        scheme = current_scheme()
        scrim, text = role_color("welcome_scrim", scheme), role_color("on_welcome_scrim", scheme)
        for label in (self.name_label, self.version_label):
            label.setStyleSheet(
                f"QLabel {{ background: {scrim}; color: {text}; border-radius: 4px; "
                "padding: 0 8px; }"
            )
        self._generic = None

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        scale = self.width() / ART_SIZE.width
        for label, size in ((self.name_label, 26), (self.version_label, 15)):
            font = QFont(label.font())
            font.setPixelSize(max(9, round(size * scale)))
            font.setBold(label is self.name_label)
            label.setFont(font)
        self.name_label.setGeometry(*_scaled(NAME_PANEL, scale))
        # The version's scrim hugs its text, at the right of its safe area.
        x, y, width, height = _scaled(VERSION_LINE, scale)
        fitted = min(width, self.version_label.sizeHint().width())
        self.version_label.setGeometry(x + width - fitted, y, fitted, height)
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
        width = image.width() / image.devicePixelRatio()
        height = image.height() / image.devicePixelRatio()
        crop = cover_crop(Size(width, height), Size(target.width(), target.height()), self._focus)
        r = image.devicePixelRatio()
        p.drawImage(target, image, QRectF(crop.x * r, crop.y * r, crop.width * r, crop.height * r))
        p.end()


def _scaled(area: Rect, scale: float) -> tuple[int, int, int, int]:
    return (
        round(area.x * scale),
        round(area.y * scale),
        round(area.width * scale),
        round(area.height * scale),
    )


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

        scale = self._fit_scale()
        self.setFixedSize(round(WINDOW.width * scale), round(WINDOW.height * scale))

        self.top_bar = _TopBar(self)
        self.top_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.top_bar.setFixedHeight(round(TOP_BAR * scale))
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
        bar = QHBoxLayout(self.top_bar)
        bar.setContentsMargins(4, 0, 4, 0)
        bar.addStretch(1)
        bar.addWidget(self.about_button)
        bar.addWidget(self.close_button)

        self.logo = _LogoStrip(branding, self)
        self.logo.setFixedWidth(round(LOGO_STRIP * scale))
        self.art = _ArtSlot(branding, self)
        self.art.setFixedSize(round(ART_SIZE.width * scale), round(ART_SIZE.height * scale))
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
        self.art.apply_theme()

    def _on_color_scheme_changed(self, *_args: object) -> None:
        self._apply_theme()
        self.update()

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
