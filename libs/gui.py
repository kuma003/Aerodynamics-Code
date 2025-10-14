import os

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtWidgets

from .tabs.launch_site import LaunchSiteTab
from .tabs.simulation import SimulationTab


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
        self.side_panel.setMaximumWidth(400)
        self.side_panel.setLayout(self.side_panel_layout)
        self.addWidget(self.side_panel)

        self.tab_widget = QtWidgets.QTabWidget()
        self.side_panel_layout.addWidget(self.tab_widget)

        self.simulation_tab = SimulationTab(self)
        self.tab_widget.addTab(self.simulation_tab, "シミュレーション")

        self.launch_site_tab = LaunchSiteTab(self.icon_dir, self)
        self.tab_widget.addTab(self.launch_site_tab, "射場")

        main_layout = QtWidgets.QVBoxLayout()

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)

        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        toggle_button = QtWidgets.QPushButton("サイドパネル表示切替")
        main_layout.addWidget(toggle_button)

        self.addWidget(central_widget)

        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setCollapsible(0, False)
        self.setCollapsible(1, False)
