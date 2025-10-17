from __future__ import annotations

import abc
from pathlib import Path
from typing import Optional

import pyqtgraph as pg
from PySide6.QtSvg import QSvgGenerator
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from ..widgets import AspectRatioContainer


class GraphBase(abc.ABC):
    """Common functionality for graphs displayed in the GUI."""

    MM_PER_INCH = 25.4

    def __init__(
        self,
        *,
        name: str,
        width: int,
        height: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        self.name = name
        self.plot_widget = self._create_plot_widget()
        self.container = AspectRatioContainer(
            self.plot_widget, width=width, height=height, parent=parent
        )
        self._base_y_over_x_ratio = self._compute_y_over_x_ratio(width, height)
        self._viewbox_lock_enabled = False
        self._viewbox_x_range: Optional[tuple[float, float]] = None
        self._viewbox_y_range: Optional[tuple[float, float]] = None
        self._viewbox_ratio_override: Optional[float] = None
        self._initialize_plot()

    def set_base_dimensions(self, width: int, height: int, dpi: int) -> None:
        width = max(1, width)
        height = max(1, height)
        self.container.set_ratio(width, height)
        self._base_y_over_x_ratio = self._compute_y_over_x_ratio(width, height)
        self._update_viewbox_aspect_lock()
        self.plot_widget.setToolTip(
            f"ベースサイズ: {width} x {height} px / DPI {dpi}"
        )

    def export_to_path(
        self,
        destination: Path,
        *,
        format_name: str,
        width: int,
        height: int,
        dpi: int,
    ) -> None:
        destination = destination.with_suffix(f".{format_name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        width = max(1, width)
        height = max(1, height)

        QtWidgets.QApplication.processEvents()

        if format_name == "png":
            image = self._render_to_image(width, height, dpi)
            if not image.save(str(destination), "PNG"):
                raise RuntimeError("PNG 画像を書き込めませんでした。")
        elif format_name == "svg":
            self._export_svg(destination, width, height, dpi)
        elif format_name == "pdf":
            self._export_pdf(destination, width, height, dpi)
        else:
            raise ValueError(f"未対応の形式です: {format_name}")

    def update_site_coordinate(self, coord: Optional[tuple[float, float]]) -> None:
        """Hook for graphs that react to site coordinate changes."""

    # --- hooks for subclasses -------------------------------------------------

    @abc.abstractmethod
    def _initialize_plot(self) -> None:
        """Populate the plot widget with graph-specific contents."""

    # --- helpers --------------------------------------------------------------

    def _create_plot_widget(self) -> pg.PlotWidget:
        plot = pg.PlotWidget(background="w")
        plot.setMenuEnabled(False)
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.getPlotItem().setDownsampling(mode="peak")
        plot.getPlotItem().setClipToView(True)
        return plot

    def _render_to_image(self, width: int, height: int, dpi: int) -> QtGui.QImage:
        image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtGui.QColor("white"))
        dots_per_meter = int(dpi * 39.37007874)
        image.setDotsPerMeterX(dots_per_meter)
        image.setDotsPerMeterY(dots_per_meter)
        painter = QtGui.QPainter(image)
        target_rect = QtCore.QRect(0, 0, width, height)
        source_rect = self.plot_widget.rect()
        self.plot_widget.render(painter, target_rect, source_rect)
        painter.end()
        return image

    def _export_svg(
        self,
        destination: Path,
        width: int,
        height: int,
        dpi: int,
    ) -> None:
        generator = QSvgGenerator()
        generator.setFileName(str(destination))
        generator.setSize(QtCore.QSize(width, height))
        generator.setViewBox(QtCore.QRect(0, 0, width, height))
        generator.setResolution(dpi)
        painter = QtGui.QPainter(generator)
        self.plot_widget.render(painter)
        painter.end()

    def _export_pdf(
        self,
        destination: Path,
        width: int,
        height: int,
        dpi: int,
    ) -> None:
        image = self._render_to_image(width, height, dpi)
        pdf_writer = QtGui.QPdfWriter(str(destination))
        pdf_writer.setResolution(dpi)
        page_width_mm = width / dpi * self.MM_PER_INCH
        page_height_mm = height / dpi * self.MM_PER_INCH
        pdf_writer.setPageMargins(QtCore.QMarginsF(0, 0, 0, 0))
        pdf_writer.setPageSizeMM(QtCore.QSizeF(page_width_mm, page_height_mm))

        painter = QtGui.QPainter(pdf_writer)
        target_rect = QtCore.QRectF(0, 0, pdf_writer.width(), pdf_writer.height())
        painter.drawImage(target_rect, image)
        painter.end()

    def lock_viewbox_aspect(
        self,
        *,
        x_range: Optional[tuple[float, float]] = None,
        y_range: Optional[tuple[float, float]] = None,
        ratio: Optional[float] = None,
    ) -> None:
        """Lock the view box aspect to a fixed ratio and range."""

        self._viewbox_lock_enabled = True
        self._viewbox_x_range = x_range
        self._viewbox_y_range = y_range
        self._viewbox_ratio_override = ratio
        self._update_viewbox_aspect_lock()

    def unlock_viewbox_aspect(self) -> None:
        """Allow the view box to auto-scale without aspect locking."""

        self._viewbox_lock_enabled = False
        self._viewbox_ratio_override = None
        self._viewbox_x_range = None
        self._viewbox_y_range = None
        view_box = self.plot_widget.getPlotItem().getViewBox()
        view_box.setAspectLocked(False)
        view_box.enableAutoRange(True, True)

    def _configure_viewbox(
        self,
        *,
        lock_aspect: bool = False,
        ratio: float = 1.0,
        x_range: Optional[tuple[float, float]] = None,
        y_range: Optional[tuple[float, float]] = None,
    ) -> None:
        view_box = self.plot_widget.getPlotItem().getViewBox()
        view_box.setDefaultPadding(0.0)
        if lock_aspect:
            view_box.setAspectLocked(True, ratio=ratio)
        if x_range is not None:
            view_box.setXRange(*x_range, padding=0.0)
        if y_range is not None:
            view_box.setYRange(*y_range, padding=0.0)
        view_box.enableAutoRange(False, False)

    def _update_viewbox_aspect_lock(self) -> None:
        if not self._viewbox_lock_enabled:
            return
        ratio = self._determine_viewbox_ratio()
        self._configure_viewbox(
            lock_aspect=True,
            ratio=ratio,
            x_range=self._viewbox_x_range,
            y_range=self._viewbox_y_range,
        )

    def _determine_viewbox_ratio(self) -> float:
        if self._viewbox_ratio_override is not None and self._viewbox_ratio_override > 0:
            return self._viewbox_ratio_override
        if (
            self._viewbox_x_range is not None
            and self._viewbox_y_range is not None
            and self._viewbox_x_range[1] != self._viewbox_x_range[0]
        ):
            x_span = self._viewbox_x_range[1] - self._viewbox_x_range[0]
            y_span = self._viewbox_y_range[1] - self._viewbox_y_range[0]
            if x_span and y_span:
                return abs(y_span / x_span)
        return self._base_y_over_x_ratio if self._base_y_over_x_ratio > 0 else 1.0

    @staticmethod
    def _compute_y_over_x_ratio(width: int, height: int) -> float:
        if width <= 0 or height <= 0:
            return 1.0
        return height / width


__all__ = ["GraphBase"]
