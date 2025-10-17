import math
import os
import re
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from PySide6.QtSvg import QSvgGenerator
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from .tabs import SimulationTab, LaunchSiteTab, GraphConfigTab


class AspectRatioContainer(QtWidgets.QWidget):
    def __init__(
        self,
        content: QtWidgets.QWidget,
        *,
        width: int = 4,
        height: int = 3,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._content = content
        self._ratio = self._compute_ratio(width, height)
        self._content.setParent(self)
        self._content.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored,
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def set_ratio(self, width: int, height: int) -> None:
        self._ratio = self._compute_ratio(width, height)
        self._relayout()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._relayout()

    def sizeHint(self) -> QtCore.QSize:
        hint = self._content.sizeHint()
        if self._ratio <= 0:
            return hint
        width = hint.width()
        height = hint.height()
        if height <= 0:
            height = max(1, int(width / self._ratio))
        return QtCore.QSize(width, height)

    @staticmethod
    def _compute_ratio(width: int, height: int) -> float:
        if width <= 0 or height <= 0:
            return 0.0
        return width / height

    def _relayout(self) -> None:
        if not self._content:
            return

        rect = self.rect()
        if rect.isEmpty():
            return

        if self._ratio <= 0:
            self._content.setGeometry(rect)
            return

        available_width = rect.width()
        available_height = rect.height()

        target_width = min(available_width, int(available_height * self._ratio))
        target_height = min(available_height, int(available_width / self._ratio))

        # Recompute in case rounding created a mismatch.
        if target_width / max(target_height, 1) > self._ratio:
            target_width = int(target_height * self._ratio)
        else:
            target_height = int(target_width / self._ratio)

        offset_x = rect.x() + (available_width - target_width) // 2
        offset_y = rect.y() + (available_height - target_height) // 2

        self._content.setGeometry(
            QtCore.QRect(offset_x, offset_y, target_width, target_height)
        )


class GraphView:
    def __init__(
        self,
        name: str,
        plot_widget: pg.PlotWidget,
        container: AspectRatioContainer,
        initializer: Optional[Callable[[pg.PlotWidget], None]] = None,
    ) -> None:
        self.name = name
        self.plot_widget = plot_widget
        self.container = container
        if initializer is not None:
            initializer(self.plot_widget)


class GraphDisplayArea(QtWidgets.QWidget):
    MM_PER_INCH = 25.4

    def __init__(
        self,
        config_tab: GraphConfigTab,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config_tab = config_tab
        self._graphs: list[GraphView] = []
        self._site_marker: Optional[pg.PlotDataItem] = None
        self._random_seed = np.random.default_rng(42)
        self._build_ui()
        self._create_graphs()
        self._config_tab.graph_settings_changed.connect(self._apply_graph_settings)
        self._apply_graph_settings()

    def update_site_coordinate(self, coord: Optional[Tuple[float, float]]) -> None:
        if self._site_marker is None:
            return

        if coord is None:
            self._site_marker.setData([], [])
            self._site_marker.setToolTip("")
        else:
            lat, lon = coord
            self._site_marker.setData([0.0], [0.0])
            # Show actual coordinate via tooltip while keeping the marker inside the fixed view.
            self._site_marker.setToolTip(f"緯度: {lat:.5f}\n経度: {lon:.5f}")

    # --- internal helpers -------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.setLayout(layout)

        self._graph_tab_widget = QtWidgets.QTabWidget()
        self._graph_tab_widget.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self._graph_tab_widget.setDocumentMode(True)
        self._graph_tab_widget.setElideMode(QtCore.Qt.TextElideMode.ElideRight)
        layout.addWidget(self._graph_tab_widget, 1)

        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.addStretch(1)

        self._export_current_button = QtWidgets.QPushButton("表示中のグラフを保存")
        self._export_current_button.clicked.connect(self._export_current_graph)
        controls_layout.addWidget(self._export_current_button)

        self._export_all_button = QtWidgets.QPushButton("すべてのグラフを保存")
        self._export_all_button.clicked.connect(self._export_all_graphs)
        controls_layout.addWidget(self._export_all_button)

        layout.addLayout(controls_layout)

    def _create_graphs(self) -> None:
        self._graphs.clear()

        def create_plot() -> pg.PlotWidget:
            plot = pg.PlotWidget(background="w")
            plot.setMenuEnabled(False)
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.getPlotItem().setDownsampling(mode="peak")
            plot.getPlotItem().setClipToView(True)
            return plot

        graph_definitions: list[tuple[str, Callable[[pg.PlotWidget], None]]] = [
            ("高度プロファイル", self._populate_altitude_profile),
            ("風速プロファイル", self._populate_wind_profile),
            ("着地予測散布", self._populate_landing_distribution),
        ]

        width, height = self._config_tab.graph_dimensions()

        for name, initializer in graph_definitions:
            plot_widget = create_plot()
            container = AspectRatioContainer(
                plot_widget, width=width, height=height, parent=self
            )
            graph = GraphView(name, plot_widget, container, initializer)
            self._graphs.append(graph)
            self._graph_tab_widget.addTab(container, name)

        if self._graphs:
            self._graph_tab_widget.setCurrentIndex(0)

    def _populate_altitude_profile(self, plot: pg.PlotWidget) -> None:
        time_s = np.linspace(0, 180, 200)
        altitude_m = 1500 * np.exp(-time_s / 120) + 100 * np.sin(time_s / 8)
        plot.plot(time_s, altitude_m, pen=pg.mkPen("#1976d2", width=2))
        plot.setLabel("bottom", "時間", units="s")
        plot.setLabel("left", "高度", units="m")
        plot.setTitle("模擬高度プロファイル", color="#0d47a1")

    def _populate_wind_profile(self, plot: pg.PlotWidget) -> None:
        altitude = np.linspace(0, 3000, 40)
        base_speed = 5 + 3 * np.cos(altitude / 800)
        gust_component = 0.8 * np.sin(altitude / 120)
        speed = base_speed + gust_component
        plot.plot(speed, altitude, pen=pg.mkPen("#388e3c", width=2))
        plot.setLabel("bottom", "風速", units="m/s")
        plot.setLabel("left", "高度", units="m")
        plot.setTitle("推定風速プロファイル", color="#1b5e20")

    def _populate_landing_distribution(self, plot: pg.PlotWidget) -> None:
        theta = np.linspace(0, 2 * math.pi, 80, endpoint=False)
        radius = 0.75 + 0.1 * self._random_seed.random(theta.size)
        x_vals = radius * np.cos(theta)
        y_vals = radius * np.sin(theta)
        plot.plot(
            x_vals,
            y_vals,
            pen=None,
            symbol="o",
            symbolPen=pg.mkPen(color="#0277bd"),
            symbolSize=7,
            symbolBrush=pg.mkBrush("#4fc3f7"),
            name="シミュ散布",
        )

        # Marker updated when射場座標 changes.
        self._site_marker = plot.plot(
            [],
            [],
            pen=None,
            symbol="star",
            symbolSize=16,
            symbolBrush=pg.mkBrush("#d32f2f"),
            symbolPen=pg.mkPen("#b71c1c", width=1.5),
            name="射場",
        )

        plot.addLegend(offset=(10, 10))
        plot.setLabel("bottom", "東西偏差", units="km")
        plot.setLabel("left", "南北偏差", units="km")
        plot.setTitle("着地予測散布", color="#01579b")
        plot.setXRange(-1.2, 1.2)
        plot.setYRange(-1.2, 1.2)
        plot.setAspectLocked(True, 1.0)

    def _apply_graph_settings(self) -> None:
        width, height = self._config_tab.graph_dimensions()
        width = max(width, 1)
        height = max(height, 1)
        for graph in self._graphs:
            graph.container.set_ratio(width, height)
            graph.plot_widget.setToolTip(
                f"ベースサイズ: {width} x {height} px / DPI {self._config_tab.graph_dpi()}"
            )

    def _export_current_graph(self) -> None:
        graph = self._current_graph()
        if graph is None:
            return
        format_name = self._config_tab.graph_format()
        default_name = f"{self._sanitize_filename(graph.name)}.{format_name}"
        start_dir = Path(os.getcwd()) / default_name
        caption = "グラフを保存"
        filter_map = {
            "png": "PNG (*.png)",
            "svg": "SVG (*.svg)",
            "pdf": "PDF (*.pdf)",
        }
        file_path_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption,
            str(start_dir),
            filter_map.get(format_name, "すべてのファイル (*)"),
        )
        if not file_path_str:
            return
        try:
            self._export_graph_to_path(graph, Path(file_path_str))
            QtWidgets.QMessageBox.information(
                self, "保存完了", "グラフを保存しました。"
            )
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(
                self,
                "保存エラー",
                f"グラフの保存に失敗しました。\n{exc}",
            )

    def _export_all_graphs(self) -> None:
        if not self._graphs:
            return

        output_dir_str = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "保存先フォルダを選択",
            str(Path(os.getcwd())),
        )
        if not output_dir_str:
            return
        output_dir = Path(output_dir_str)
        failures: list[str] = []
        for graph in self._graphs:
            try:
                destination = output_dir / (
                    f"{self._sanitize_filename(graph.name)}."
                    f"{self._config_tab.graph_format()}"
                )
                self._export_graph_to_path(graph, destination)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{graph.name}: {exc}")

        if failures:
            QtWidgets.QMessageBox.warning(
                self,
                "一部エラー",
                "\n".join(failures),
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "保存完了",
                "すべてのグラフを保存しました。",
            )

    def _export_graph_to_path(self, graph: GraphView, destination: Path) -> None:
        destination = destination.with_suffix(f".{self._config_tab.graph_format()}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        width, height = self._config_tab.graph_dimensions()
        dpi = self._config_tab.graph_dpi()
        format_name = self._config_tab.graph_format()

        QtWidgets.QApplication.processEvents()

        if format_name == "png":
            image = self._render_to_image(graph, width, height, dpi)
            if not image.save(str(destination), "PNG"):
                raise RuntimeError("PNG 画像を書き込めませんでした。")
        elif format_name == "svg":
            self._export_svg(graph, destination, width, height, dpi)
        elif format_name == "pdf":
            self._export_pdf(graph, destination, width, height, dpi)
        else:
            raise ValueError(f"未対応の形式です: {format_name}")

    def _render_to_image(
        self, graph: GraphView, width: int, height: int, dpi: int
    ) -> QtGui.QImage:
        width = max(1, width)
        height = max(1, height)
        image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtGui.QColor("white"))
        dots_per_meter = int(dpi * 39.37007874)
        image.setDotsPerMeterX(dots_per_meter)
        image.setDotsPerMeterY(dots_per_meter)
        painter = QtGui.QPainter(image)
        target_rect = QtCore.QRect(0, 0, width, height)
        source_rect = graph.plot_widget.rect()
        graph.plot_widget.render(painter, target_rect, source_rect)
        painter.end()
        return image

    def _export_svg(
        self,
        graph: GraphView,
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
        graph.plot_widget.render(painter)
        painter.end()

    def _export_pdf(
        self,
        graph: GraphView,
        destination: Path,
        width: int,
        height: int,
        dpi: int,
    ) -> None:
        image = self._render_to_image(graph, width, height, dpi)
        pdf_writer = QtGui.QPdfWriter(str(destination))
        pdf_writer.setResolution(dpi)
        page_width_mm = width / dpi * self.MM_PER_INCH
        page_height_mm = height / dpi * self.MM_PER_INCH
        pdf_writer.setPageMargins(QtCore.QMarginsF(0, 0, 0, 0))
        pdf_writer.setPageSizeMM(QtCore.QSizeF(page_width_mm, page_height_mm))

        painter = QtGui.QPainter(pdf_writer)
        target_rect = QtCore.QRectF(
            0,
            0,
            pdf_writer.width(),
            pdf_writer.height(),
        )
        painter.drawImage(target_rect, image)
        painter.end()

    def _current_graph(self) -> Optional[GraphView]:
        index = self._graph_tab_widget.currentIndex()
        if 0 <= index < len(self._graphs):
            return self._graphs[index]
        return None

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        sanitized = re.sub(r"\s+", "_", name.strip())
        sanitized = re.sub(r"[^0-9A-Za-z_\-一-龥ぁ-んァ-ンー]", "", sanitized)
        return sanitized or "graph"


class MainWindow(QtWidgets.QSplitter):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("散布プロット")
        self.setGeometry(100, 100, 1000, 800)

        font = QtGui.QFont()
        font.setPointSize(10)
        self.setFont(font)

        self.icon_dir = os.path.join(os.path.dirname(__file__), "icons")

        self._build_ui()

    def _build_ui(self) -> None:
        self.side_panel_layout = QtWidgets.QVBoxLayout()

        self.side_panel = QtWidgets.QWidget()
        self.side_panel.setMinimumWidth(400)
        self.side_panel.setLayout(self.side_panel_layout)
        self.addWidget(self.side_panel)

        self.tab_widget = QtWidgets.QTabWidget()
        self.side_panel_layout.addWidget(self.tab_widget)

        self.simulation_tab = SimulationTab(self)
        self.tab_widget.addTab(self.simulation_tab, "シミュレーション")

        self.launch_site_tab = LaunchSiteTab(self.icon_dir, self)
        self.tab_widget.addTab(self.launch_site_tab, "射場")

        self.map_config_tab = GraphConfigTab(self)
        self.tab_widget.addTab(self.map_config_tab, "グラフ")

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)

        self.graph_area = GraphDisplayArea(self.map_config_tab, self)
        main_layout.addWidget(self.graph_area, 1)

        self.addWidget(central_widget)

        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setCollapsible(0, True)
        self.setCollapsible(1, False)

        self.launch_site_tab.site_centroid_changed.connect(
            self._on_site_centroid_changed
        )
        self._on_site_centroid_changed(
            self.launch_site_tab.compute_site_centroid()
        )

    def _on_site_centroid_changed(self, coord: Optional[Tuple[float, float]]) -> None:
        self.map_config_tab.set_site_coordinate(coord)
        self.graph_area.update_site_coordinate(coord)
