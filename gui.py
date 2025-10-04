import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.Qt.QtWidgets import (
    QSplitter,
    QVBoxLayout,
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
)


class MainWindow(QSplitter):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScatterPlot")
        self.setGeometry(100, 100, 800, 600)

        self.initUI()
        self.setHandleWidth(0)  # not to show line when side pannel closed.

    def initUI(self):
        # Create side panel layout
        self.side_panel_layout = QVBoxLayout()

        # Create side panel widget
        self.side_panel = QWidget()
        self.side_panel.setFixedWidth(400)  # Set a fixed width for the side panel
        self.side_panel.setLayout(self.side_panel_layout)

        # Add the side panel to the splitter
        self.addWidget(self.side_panel)

        # Add import button to the side panel
        kml_import_button = QtWidgets.QPushButton("Import KML")
        # kml_import_button.clicked.connect(self.import_kml)
        self.side_panel_layout.addWidget(kml_import_button)

        # Add some example content to the side panel
        self.side_panel_layout.addWidget(QtWidgets.QLabel("Side Panel"))
        self.side_panel_layout.addWidget(QtWidgets.QPushButton("Button 1"))
        self.side_panel_layout.addWidget(QtWidgets.QPushButton("Button 2"))

        # Create main layout
        main_layout = QVBoxLayout()

        # Create a central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        # Create a plot widget
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        # Add the central widget to the splitter
        self.addWidget(central_widget)

        # Add a button to toggle the side panel visibility
        toggle_button = QtWidgets.QPushButton("Toggle Side Panel")
        # toggle_button.clicked.connect(self.toggle_side_panel)
        main_layout.addWidget(toggle_button)

    def build_tree(self, parent_item, node_dict):
        for name, children in node_dict.items():
            item = QTreeWidgetItem([name])
            if parent_item is None:
                raise Exception("parent_item is None")
            parent_item.addChild(item)

            if children and isinstance(children, dict):
                # 親ノード
                self.build_tree(item, children)
            else:
                # 葉ノード
                pass
