import os
import random
from typing import Any, Optional

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from shapely.geometry import LineString, Point, Polygon

from ..kml_reader import kml_folder, kml_placemark, read_kml
from ..ui_helpers import create_section_title

ROLE_VISIBLE = QtCore.Qt.ItemDataRole.UserRole
ROLE_COLOR = ROLE_VISIBLE + 1
ROLE_ZONE = ROLE_COLOR + 1
ROLE_GEOMETRY = ROLE_ZONE + 1


class LaunchSiteTab(QtWidgets.QWidget):
    def __init__(self, icon_dir: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.icon_dir = icon_dir
        self.visible_icon_path = os.path.join(self.icon_dir, "visibility.svg")
        self.invisible_icon_path = os.path.join(self.icon_dir, "visibility_off.svg")
        self.visible_icon = QtGui.QIcon(self.visible_icon_path)
        self.invisible_icon = QtGui.QIcon(self.invisible_icon_path)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(create_section_title("射場設定"))

        kml_import_button = QtWidgets.QPushButton("KMLをインポート")
        kml_import_button.clicked.connect(self.import_kml)
        layout.addWidget(kml_import_button)

        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setFrameShape(QtWidgets.QFrame.Shape.Box)
        self.tree_widget.setLineWidth(1)
        self.tree_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.tree_widget.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        header = self.tree_widget.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.tree_widget.setColumnWidth(1, 28)
        self.tree_widget.setColumnWidth(2, 40)
        self.tree_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.tree_widget.clear()
        self.tree_widget.itemClicked.connect(self.on_item_clicked)

        self.launch_site_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.launch_site_splitter.addWidget(self.tree_widget)

        self.launch_site_info = QtWidgets.QTextEdit()
        self.launch_site_info.setReadOnly(True)
        self.launch_site_info.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.launch_site_info.setHtml(
            "<b>射点座標</b><br>"
            "緯度: <br>"
            "経度: <br>"
            "<b>射場重心</b><br>"
            "緯度: <br>"
            "経度: <br>"
        )
        self.launch_site_info.setMinimumHeight(120)
        self.launch_site_splitter.addWidget(self.launch_site_info)
        self.launch_site_splitter.setStretchFactor(0, 3)
        self.launch_site_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.launch_site_splitter)

    def import_kml(self) -> None:
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.Option.ReadOnly
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "KMLファイルを選択",
            "",
            "KML Files (*.kml);;All Files (*)",
            options=options,
        )
        if file_path:
            try:
                kml_data = read_kml(file_path)
                self.build_tree_from_kml(kml_data)
                print("KMLデータが正常に読み込まれました。")
            except Exception as exc:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(
                    self,
                    "エラー",
                    f"KMLファイルの読み込み中にエラーが発生しました:\n{exc}",
                )

    def build_tree_from_kml(self, root_folder: Optional[kml_folder]) -> None:
        self.tree_widget.clear()
        if root_folder is None:
            return

        self._add_folder_item(self.tree_widget.invisibleRootItem(), root_folder)
        self.tree_widget.expandAll()

    def _add_folder_item(
        self, parent_item: QtWidgets.QTreeWidgetItem, folder: kml_folder
    ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([folder.name or "Unnamed Folder"])
        parent_item.addChild(item)

        for child_folder in folder.folders or []:
            self._add_folder_item(item, child_folder)

        if folder.placemarks:
            shared_leaf_color = self._generate_random_color()
            for placemark in folder.placemarks:
                self._add_placemark_item(item, placemark, shared_leaf_color)

        if self.get_all_leaf_nodes(item):
            self.create_toggle_button(item)

        return item

    def _add_placemark_item(
        self,
        parent_item: QtWidgets.QTreeWidgetItem,
        placemark: kml_placemark,
        shared_color: QtGui.QColor,
    ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([placemark.name or "Unnamed Placemark"])
        parent_item.addChild(item)

        color = QtGui.QColor(shared_color)
        item.setData(0, ROLE_VISIBLE, True)
        item.setData(0, ROLE_COLOR, color)
        item.setData(0, ROLE_ZONE, "forbidden")
        item.setData(0, ROLE_GEOMETRY, placemark.geometry)
        tooltip = self._format_geometry_tooltip(placemark.geometry)
        if tooltip:
            item.setToolTip(0, tooltip)
            item.setToolTip(1, tooltip)
            item.setToolTip(2, tooltip)
        self._apply_item_color(item, color)
        self.create_color_button(item)

        return item

    def _format_geometry_tooltip(self, geometry: Any) -> str:
        if geometry is None:
            return ""

        if isinstance(geometry, Point):
            lat = geometry.y
            lon = geometry.x
            return "タイプ: 点\n" f"緯度: {lat:.6f}\n" f"経度: {lon:.6f}"

        if isinstance(geometry, LineString):
            coords = list(geometry.coords)
            return f"タイプ: 線 ({len(coords)} 点)"

        if isinstance(geometry, Polygon):
            exterior_coords = (
                list(geometry.exterior.coords) if geometry.exterior else []
            )
            header = f"タイプ: ポリゴン ({len(exterior_coords)} 点)"
            lat = geometry.centroid.y
            lon = geometry.centroid.x
            return f"{header}\n重心緯度: {lat:.6f}\n重心経度: {lon:.6f}"

        return f"タイプ: {getattr(geometry, 'geom_type', '不明')}"

    def create_toggle_button(self, parent_item: QtWidgets.QTreeWidgetItem) -> None:
        toggle_button = QtWidgets.QPushButton()
        toggle_button.setFlat(True)
        toggle_button.setMaximumSize(24, 24)
        toggle_button.setIconSize(QtCore.QSize(20, 20))
        self.update_toggle_button_icon(toggle_button, True)
        toggle_button.clicked.connect(
            lambda checked, btn=toggle_button, it=parent_item: self.toggle_all_children(
                btn, it
            )
        )
        self.tree_widget.setItemWidget(parent_item, 2, toggle_button)

    def create_color_button(self, item: QtWidgets.QTreeWidgetItem) -> None:
        color_button = QtWidgets.QPushButton()
        color_button.setFlat(True)
        color_button.setFixedSize(15, 15)
        color_button.clicked.connect(
            lambda checked=False, it=item: self.on_color_button_clicked(it)
        )
        self.tree_widget.setItemWidget(item, 1, color_button)
        zone_button = self.create_zone_button(item)

        color = item.data(0, ROLE_COLOR)
        if isinstance(color, QtGui.QColor):
            self._update_color_button_appearance(color_button, color)

        tooltip = self._format_geometry_tooltip(item.data(0, ROLE_GEOMETRY))
        if tooltip:
            color_button.setToolTip(tooltip)
            if zone_button is not None:
                zone_button.setToolTip(tooltip)

    def on_color_button_clicked(self, item: QtWidgets.QTreeWidgetItem) -> None:
        current_color = item.data(0, ROLE_COLOR)
        if not isinstance(current_color, QtGui.QColor):
            current_color = QtGui.QColor(QtCore.Qt.GlobalColor.black)

        selected_color = QtWidgets.QColorDialog.getColor(
            current_color, self, "色を選択"
        )
        if selected_color.isValid():
            item.setData(0, ROLE_COLOR, selected_color)
            self._apply_item_color(item, selected_color)

            button = self.tree_widget.itemWidget(item, 1)
            if isinstance(button, QtWidgets.QPushButton):
                self._update_color_button_appearance(button, selected_color)

    def _update_color_button_appearance(
        self, button: QtWidgets.QPushButton, color: QtGui.QColor
    ) -> None:
        button.setStyleSheet(
            "QPushButton {"
            f"background-color: {color.name()};"
            "border: 1px solid #666;"
            "padding: 0px;"
            "}"
        )

    def create_zone_button(
        self, item: QtWidgets.QTreeWidgetItem
    ) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton()
        btn.setFlat(True)
        btn.setCheckable(True)
        btn.setFixedSize(28, 20)

        zone = item.data(0, ROLE_ZONE)
        if zone is None:
            zone = "forbidden"
            item.setData(0, ROLE_ZONE, zone)

        def _apply_zone_appearance(
            button: QtWidgets.QPushButton, zone_value: str
        ) -> None:
            if zone_value == "allowed":
                button.setChecked(True)
                button.setText("〇")
                button.setStyleSheet("QPushButton { color: green; font-weight: bold; }")
            else:
                button.setChecked(False)
                button.setText("×")
                button.setStyleSheet("QPushButton { color: red; font-weight: bold; }")

        _apply_zone_appearance(btn, zone)

        def _on_zone_toggled(checked: bool, it=item, button=btn) -> None:
            new_zone = "allowed" if checked else "forbidden"
            it.setData(0, ROLE_ZONE, new_zone)
            _apply_zone_appearance(button, new_zone)

        btn.toggled.connect(_on_zone_toggled)
        self.tree_widget.setItemWidget(item, 2, btn)
        return btn

    def _generate_random_color(self) -> QtGui.QColor:
        hue = random.randint(0, 359)
        saturation = random.randint(150, 255)
        value = random.randint(180, 255)
        return QtGui.QColor.fromHsv(hue, saturation, value)

    def _apply_item_color(
        self, item: QtWidgets.QTreeWidgetItem, color: QtGui.QColor
    ) -> None:
        if item.data(0, ROLE_VISIBLE):
            base_text_color = QtGui.QColor(QtCore.Qt.GlobalColor.black)
            item.setForeground(0, QtGui.QBrush(base_text_color))
            item.setBackground(0, QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))

    def update_toggle_button_icon(
        self, button: QtWidgets.QPushButton, all_visible: bool
    ) -> None:
        if all_visible:
            button.setIcon(self.visible_icon)
        else:
            button.setIcon(self.invisible_icon)

    def on_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        if item.childCount() == 0:
            visible = item.data(0, ROLE_VISIBLE)
            if visible is None:
                visible = True
            visible = not visible
            item.setData(0, ROLE_VISIBLE, visible)
            if visible:
                color = item.data(0, ROLE_COLOR)
                if isinstance(color, QtGui.QColor):
                    self._apply_item_color(item, color)
                else:
                    self._apply_item_color(
                        item, QtGui.QColor(QtCore.Qt.GlobalColor.black)
                    )
            else:
                item.setForeground(
                    0, QtGui.QBrush(QtGui.QColor(QtCore.Qt.GlobalColor.gray))
                )
                item.setBackground(0, QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))

    def toggle_all_children(
        self, button: QtWidgets.QPushButton, parent_item: QtWidgets.QTreeWidgetItem
    ) -> None:
        leaf_nodes = self.get_all_leaf_nodes(parent_item)
        if not leaf_nodes:
            return

        all_visible = all(node.data(0, ROLE_VISIBLE) for node in leaf_nodes)
        new_state = not all_visible
        for node in leaf_nodes:
            node.setData(0, ROLE_VISIBLE, new_state)
            if new_state:
                color = node.data(0, ROLE_COLOR)
                if isinstance(color, QtGui.QColor):
                    self._apply_item_color(node, color)
                else:
                    self._apply_item_color(
                        node, QtGui.QColor(QtCore.Qt.GlobalColor.black)
                    )
            else:
                node.setForeground(
                    0, QtGui.QBrush(QtGui.QColor(QtCore.Qt.GlobalColor.gray))
                )
                node.setBackground(0, QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))

        self.update_toggle_button_icon(button, new_state)

    def get_all_leaf_nodes(
        self, parent_item: QtWidgets.QTreeWidgetItem
    ) -> list[QtWidgets.QTreeWidgetItem]:
        leaf_nodes: list[QtWidgets.QTreeWidgetItem] = []

        def traverse(item: QtWidgets.QTreeWidgetItem) -> None:
            if item.childCount() == 0:
                leaf_nodes.append(item)
            else:
                for idx in range(item.childCount()):
                    traverse(item.child(idx))

        traverse(parent_item)
        return leaf_nodes
