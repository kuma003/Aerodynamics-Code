import os
import re
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from .graphs import (
    AltitudeProfileGraph,
    LandingDistributionGraph,
    WindProfileGraph,
)
from .graphs.base import GraphBase
from .tabs import GraphConfigTab, LaunchSiteTab, SimulationTab


class GraphDisplayArea(QtWidgets.QWidget):
    def __init__(
        self,
        config_tab: GraphConfigTab,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config_tab = config_tab
        self._graphs: list[GraphBase] = []
        self._rng = np.random.default_rng(42)
        self._build_ui()
        self._create_graphs()
        self._config_tab.graph_settings_changed.connect(self._apply_graph_settings)
        self._apply_graph_settings()

    def update_site_coordinate(self, coord: Optional[Tuple[float, float]]) -> None:
        for graph in self._graphs:
            graph.update_site_coordinate(coord)

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
        self._graph_tab_widget.clear()

        width, height = self._config_tab.graph_dimensions()

        graph_factories: list[Callable[[int, int], GraphBase]] = [
            lambda w, h: AltitudeProfileGraph(width=w, height=h, parent=self),
            lambda w, h: WindProfileGraph(width=w, height=h, parent=self),
            lambda w, h: LandingDistributionGraph(
                width=w, height=h, parent=self, rng=self._rng
            ),
        ]

        for factory in graph_factories:
            graph = factory(width, height)
            self._graphs.append(graph)
            self._graph_tab_widget.addTab(graph.container, graph.name)

        if self._graphs:
            self._graph_tab_widget.setCurrentIndex(0)

    def _apply_graph_settings(self) -> None:
        width, height = self._config_tab.graph_dimensions()
        dpi = self._config_tab.graph_dpi()
        for graph in self._graphs:
            graph.set_base_dimensions(width, height, dpi)

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

    def _export_graph_to_path(self, graph: GraphBase, destination: Path) -> None:
        width, height = self._config_tab.graph_dimensions()
        dpi = self._config_tab.graph_dpi()
        graph.export_to_path(
            destination,
            format_name=self._config_tab.graph_format(),
            width=width,
            height=height,
            dpi=dpi,
        )

    def _current_graph(self) -> Optional[GraphBase]:
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
        self._on_site_centroid_changed(self.launch_site_tab.compute_site_centroid())

    def _on_site_centroid_changed(self, coord: Optional[Tuple[float, float]]) -> None:
        self.map_config_tab.set_site_coordinate(coord)
        self.graph_area.update_site_coordinate(coord)
