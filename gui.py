import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
from pyqtgraph.Qt.QtWidgets import (
    QSplitter,
    QVBoxLayout,
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QTabWidget,
)
from pyqtgraph.Qt.QtGui import QRegularExpressionValidator
from pyqtgraph.Qt.QtCore import QRegularExpression

import os
import random

# 葉ノードに割り当てるカスタムロール
# それぞれの要素が表示されるか否かを管理
ROLE_VISIBLE = QtCore.Qt.ItemDataRole.UserRole
ROLE_COLOR = ROLE_VISIBLE + 1
ROLE_ZONE = ROLE_COLOR + 1

float_regex = QRegularExpression(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
float_input_validator = QRegularExpressionValidator(float_regex)


class MainWindow(QSplitter):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("散布プロット")
        self.setGeometry(100, 100, 1000, 800)

        # 全体的なフォントサイズを設定
        font = QtGui.QFont()
        font.setPointSize(10)  # フォントサイズを10ポイントに設定（デフォルトは通常9）
        self.setFont(font)

        # アイコンのパスを設定
        self.icon_dir = os.path.join(os.path.dirname(__file__), "icons")
        self.visible_icon_path = os.path.join(self.icon_dir, "visibility.svg")
        self.invisible_icon_path = os.path.join(self.icon_dir, "visibility_off.svg")

        # アイコンを初期化（色を黒に変更）
        self.visible_icon = QtGui.QIcon(self.visible_icon_path)
        self.invisible_icon = QtGui.QIcon(self.invisible_icon_path)

        self._updating_specific_wind = False

        self.initUI()
        # self.setHandleWidth(0)  # サイドパネルを閉じたときに線を表示しない

    def initUI(self):
        # サイドパネルのレイアウトを作成
        self.side_panel_layout = QVBoxLayout()

        # サイドパネルのウィジェットを作成
        self.side_panel = QWidget()
        self.side_panel.setMaximumWidth(400)  # サイドパネルの最大幅を設定
        self.side_panel.setLayout(self.side_panel_layout)

        # サイドパネルをスプリッターに追加
        self.addWidget(self.side_panel)

        # タブウィジェットを作成
        self.tab_widget = QTabWidget()
        self.side_panel_layout.addWidget(self.tab_widget)

        # シミュレーションタブを作成
        self.simulation_tab = QWidget()
        self.simulation_layout = QVBoxLayout()
        self.simulation_tab.setLayout(self.simulation_layout)
        self.tab_widget.addTab(self.simulation_tab, "シミュレーション")

        # 機体諸元選択
        self.simulation_layout.addWidget(
            self._create_section_title("機体諸元ファイル選択")
        )
        self.airframe_file_combo = QtWidgets.QComboBox()
        self.airframe_file_combo.addItem("選択なし", None)
        self.simulation_layout.addWidget(self.airframe_file_combo)

        self._add_separator(self.simulation_layout)

        # シミュ条件入力エリアを追加
        sim_condition_label = self._create_section_title("シミュレーション条件")
        self.simulation_layout.addWidget(sim_condition_label)
        # シミュ条件入力フォーム
        self.simulation_config_widget = self._create_simulation_config_widget()
        self.simulation_layout.addWidget(self.simulation_config_widget)

        self._add_separator(self.simulation_layout)

        # 風向・風速入力フォーム（Scatter/Detailで切り替え）
        self.simulation_layout.addWidget(self._create_section_title("風条件設定"))
        self.wind_forms_stack = QtWidgets.QStackedWidget()
        self.scatter_form_widget = self._create_scatter_form_widget()
        self.detail_form_widget = self._create_detail_form_widget()
        self.wind_forms_stack.addWidget(self.scatter_form_widget)
        self.wind_forms_stack.addWidget(self.detail_form_widget)
        max_form_height = max(
            self.scatter_form_widget.sizeHint().height(),
            self.detail_form_widget.sizeHint().height(),
        )
        self.wind_forms_stack.setFixedHeight(max_form_height)
        self.simulation_layout.addWidget(self.wind_forms_stack)

        self.simulation_mode_combo.currentIndexChanged.connect(
            self._on_sim_condition_changed
        )
        self._on_sim_condition_changed(0)

        self._add_separator(self.simulation_layout)

        # 風モデル選択
        wind_model_label = self._create_section_title("風モデル設定")
        self.simulation_layout.addWidget(wind_model_label)
        self.simulation_layout.addWidget(self._create_wind_model_form_widget())

        self._add_separator(self.simulation_layout)

        # シミュレーションタブのコンテンツ
        self.simulation_layout.addWidget(
            self._create_section_title("シミュレーション設定")
        )
        self.simulation_layout.addWidget(QtWidgets.QPushButton("実行"))
        self.simulation_layout.addStretch()  # 残りのスペースを埋める

        # 射場タブを作成
        self.launch_site_tab = QWidget()
        self.launch_site_layout = QVBoxLayout()
        self.launch_site_tab.setLayout(self.launch_site_layout)
        self.tab_widget.addTab(self.launch_site_tab, "射場")

        # シミュコンフィグを選択するトグルボタンを追加
        self.launch_site_layout.addWidget(self._create_section_title("射場設定"))

        # インポートボタンを追加
        kml_import_button = QtWidgets.QPushButton("KMLをインポート")
        # kml_import_button.clicked.connect(self.import_kml)
        self.launch_site_layout.addWidget(kml_import_button)

        # 発射地点プロパティのツリービューを追加（固定高さでスクロールバー付き）
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)  # ヘッダーを非表示
        self.tree_widget.setColumnCount(3)  # 3列に設定: ラベル, カラー, ゾーン/トグル
        self.tree_widget.setFixedHeight(300)  # fixed height
        self.tree_widget.setFrameShape(QtWidgets.QFrame.Shape.Box)  # 枠線を設定
        self.tree_widget.setLineWidth(1)  # 枠線の太さ
        self.tree_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )  # or ScrollBarAlwaysOn
        self.tree_widget.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        # 列のリサイズモードを設定
        header = self.tree_widget.header()
        header.setStretchLastSection(False)  # 最後の列を自動伸縮しない
        header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )  # 1列目は伸縮
        header.setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Fixed
        )  # 2列目は固定幅（カラー）
        header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.Fixed
        )  # 3列目は固定幅（トグル/プルダウン）
        self.tree_widget.setColumnWidth(1, 28)  # カラー列の幅
        self.tree_widget.setColumnWidth(2, 40)  # トグル / ボタン列の幅
        self.launch_site_layout.addWidget(self.tree_widget)

        # ツリー構造の例
        example_tree = {
            "射場A": {
                "項目1": {},
                "項目2": {},
                "項目3": {},
                "項目4": {},
            },
            "射場B": {
                "射場A": {
                    "項目1": {},
                    "項目2": {},
                    "項目3": {},
                    "項目4": {},
                },
                "項目2": {},
                "項目3": {},
                "項目4": {},
            },
            "射場C": {
                "項目1": {},
                "項目2": {},
                "項目3": {},
                "項目4": {},
            },
            "射場D": {
                "項目1": {},
                "項目2": {},
                "項目3": {},
                "項目4": {},
            },
        }
        self.build_tree(self.tree_widget.invisibleRootItem(), example_tree)
        self.tree_widget.expandAll()

        # 葉ノードクリック時のvisibleトグル
        self.tree_widget.itemClicked.connect(self.on_item_clicked)

        # メインレイアウトを作成
        main_layout = QVBoxLayout()

        # 中央ウィジェットを作成
        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        # プロットウィジェットを作成
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        # 中央ウィジェットをスプリッターに追加
        self.addWidget(central_widget)

        # サイドパネルの表示切り替えボタンを追加
        toggle_button = QtWidgets.QPushButton("サイドパネル表示切替")
        # toggle_button.clicked.connect(self.toggle_side_panel)
        main_layout.addWidget(toggle_button)

        # 射場の情報
        self.launch_site_info = QtWidgets.QTextEdit()
        self.launch_site_info.setReadOnly(True)
        self.launch_site_info.setLineWrapMode(
            QtWidgets.QTextEdit.LineWrapMode.NoWrap
        )  # 自動折り返しを無効化
        # HTMLフォーマットを使用してタイトルを太字に
        self.launch_site_info.setHtml(
            "<b>射点座標</b><br>"
            "緯度: <br>"
            "経度: <br>"
            "<b>射場重心</b><br>"
            "緯度: <br>"
            "経度: <br>"
        )
        self.launch_site_layout.addWidget(self.launch_site_info)

    def _create_section_title(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                font-size: 12pt;
                color: #1f2a44;
                background-color: #f0f0f0;
                border-left: 4px solid #e0e0e0;
                padding: 6px 10px;
                margin-top: 6px;
                margin-bottom: 6px;
            }
            """
        )
        return label

    def _create_form_widget(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout()
        form_layout.setLabelAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        widget.setLayout(form_layout)
        return widget

    def _add_separator(
        self,
        layout: QtWidgets.QLayout,
        top_bottom_margin: int = 4,
    ) -> QtWidgets.QFrame:
        # コンテナで上下の余白を作る
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(0, top_bottom_margin, 0, top_bottom_margin)
        container_layout.setSpacing(0)

        separator = QtWidgets.QFrame()
        # separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator.setLineWidth(1)

        # container_layout.addWidget(separator)
        layout.addWidget(container)
        return separator

    def _on_sim_condition_changed(self, index: int):
        mode = self.simulation_mode_combo.itemData(index)
        if mode:
            self._update_simulation_mode(mode)

    def _create_simulation_config_widget(self) -> QtWidgets.QWidget:
        widget = self._create_form_widget()
        form_layout: QtWidgets.QFormLayout = widget.layout()

        self.simulation_mode_combo = QtWidgets.QComboBox()
        self.simulation_mode_combo.addItem("詳細", "Detail")
        self.simulation_mode_combo.addItem("散布", "scatter")

        form_layout.addRow(
            QtWidgets.QLabel("シミュモード: "), self.simulation_mode_combo
        )

        self.falling_type = QtWidgets.QComboBox()
        self.falling_type.addItem("弾道", "trajectory")
        self.falling_type.addItem("開傘", "parachute")
        form_layout.addRow(QtWidgets.QLabel("弾道 or 開傘: "), self.falling_type)
        return widget

    def _create_scatter_form_widget(self) -> QtWidgets.QWidget:
        widget = self._create_form_widget()
        form_layout: QtWidgets.QFormLayout = widget.layout()

        self.scatter_min_speed_input = QtWidgets.QLineEdit("3.0")
        self.scatter_min_speed_input.setValidator(float_input_validator)
        form_layout.addRow(
            QtWidgets.QLabel("風速最小値 [m/s]:"), self.scatter_min_speed_input
        )

        self.scatter_max_speed_input = QtWidgets.QLineEdit("10.0")
        self.scatter_max_speed_input.setValidator(float_input_validator)
        form_layout.addRow(
            QtWidgets.QLabel("風速最大値 [m/s]:"), self.scatter_max_speed_input
        )

        self.scatter_speed_step_input = QtWidgets.QLineEdit("1.0")
        self.scatter_speed_step_input.setValidator(float_input_validator)
        form_layout.addRow(
            QtWidgets.QLabel("風向刻み幅 [deg]:"), self.scatter_speed_step_input
        )

        return widget

    def _create_detail_form_widget(self) -> QtWidgets.QWidget:
        widget = self._create_form_widget()
        form_layout: QtWidgets.QFormLayout = widget.layout()

        self.specific_wind_comb = QtWidgets.QComboBox()
        self.specific_wind_comb.addItem("選択なし", None)
        self.specific_wind_comb.addItem("無風", "no_wind")
        self.specific_wind_comb.addItem("向かい風 3m/s", "headwind_3mps")
        form_layout.addRow(QtWidgets.QLabel("特定風:"), self.specific_wind_comb)

        self.specific_wind_comb.currentIndexChanged.connect(
            self._on_specific_wind_selected
        )

        self.detail_wind_speed_input_label = QtWidgets.QLabel("風速 [m/s]:")
        self.detail_wind_speed_input = QtWidgets.QLineEdit("5.0")
        self.detail_wind_speed_input.setValidator(float_input_validator)
        form_layout.addRow(
            self.detail_wind_speed_input_label, self.detail_wind_speed_input
        )

        self.detail_wind_dir_input_label = QtWidgets.QLabel("風向 [deg]:")
        self.detail_wind_dir_input = QtWidgets.QLineEdit("90.0")
        self.detail_wind_dir_input.setValidator(float_input_validator)
        form_layout.addRow(self.detail_wind_dir_input_label, self.detail_wind_dir_input)

        return widget

    def _on_specific_wind_selected(self, index: int):
        if self._updating_specific_wind:
            return

        preset_key = self.specific_wind_comb.itemData(index)
        active = preset_key is not None

        self._updating_specific_wind = True
        try:
            self.detail_wind_dir_input_label.setEnabled(not active)
            self.detail_wind_speed_input_label.setEnabled(not active)
            self.detail_wind_speed_input.setEnabled(not active)
            self.detail_wind_dir_input.setEnabled(not active)
        finally:
            self._updating_specific_wind = False

    def _create_wind_model_form_widget(self) -> QtWidgets.QWidget:
        widget = self._create_form_widget()
        form_layout: QtWidgets.QFormLayout = widget.layout()

        self.wind_model_combo = QtWidgets.QComboBox()
        self.wind_model_combo.addItem("観測データ", "real")
        self.wind_model_combo.addItem("オリジナルモデル", "original")
        self.wind_model_combo.addItem("べき乗則のみ", "only_powerlow")
        self.wind_model_combo.addItem("無風", "no_wind")
        self.wind_model_combo.setCurrentIndex(2)
        form_layout.addRow(QtWidgets.QLabel("風モデル:"), self.wind_model_combo)

        self.power_constant_input = QtWidgets.QLineEdit("7.0")
        self.power_constant_label = QtWidgets.QLabel("べき定数:")
        form_layout.addRow(self.power_constant_label, self.power_constant_input)

        self.power_low_base_alt = QtWidgets.QLineEdit("2.0")
        self.power_low_base_alt_label = QtWidgets.QLabel("基準高度 [m]:")
        form_layout.addRow(self.power_low_base_alt_label, self.power_low_base_alt)

        self.real_data_combo = QtWidgets.QComboBox()
        self.real_data_combo.addItems(["ERA5", "MERRA-2"])
        self.real_data_label = QtWidgets.QLabel("実データソース:")
        form_layout.addRow(self.real_data_label, self.real_data_combo)

        self.wind_model_combo.currentIndexChanged.connect(self._on_wind_model_changed)
        self._on_wind_model_changed(self.wind_model_combo.currentIndex())

        return widget

    def _update_simulation_mode(self, mode: str):
        if mode == "Scatter":
            self.wind_forms_stack.setCurrentWidget(self.scatter_form_widget)
        else:
            self.wind_forms_stack.setCurrentWidget(self.detail_form_widget)

    def _on_wind_model_changed(self, index: int):
        mode = self.wind_model_combo.itemData(index)

        enable_power_fields = mode in {"original", "only_powerlow"}
        enable_real_data = mode == "real"
        disable_all = mode == "no_wind"

        self.power_constant_input.setEnabled(enable_power_fields and not disable_all)
        self.power_low_base_alt.setEnabled(enable_power_fields and not disable_all)
        self.power_constant_label.setEnabled(enable_power_fields and not disable_all)
        self.power_low_base_alt_label.setEnabled(
            enable_power_fields and not disable_all
        )

        self.real_data_combo.setEnabled(enable_real_data)
        self.real_data_label.setEnabled(enable_real_data)

    def build_tree(self, parent_item, node_dict):
        if parent_item is None:
            raise Exception("parent_item is None")

        shared_leaf_color = None
        for name, children in node_dict.items():
            item = QTreeWidgetItem([name])
            parent_item.addChild(item)

            if children and isinstance(children, dict) and children:
                # 親ノード
                self.build_tree(item, children)
                # 親ノードには一括切り替えアイコンボタンを追加
                self.create_toggle_button(item)
            else:
                # 葉ノード: 同じ親階層で共通の色を使用
                if shared_leaf_color is None:
                    shared_leaf_color = self._generate_random_color()
                color = QtGui.QColor(shared_leaf_color)
                item.setData(0, ROLE_VISIBLE, True)
                item.setData(0, ROLE_COLOR, color)
                # デフォルトは落下禁止域（×）にする
                item.setData(0, ROLE_ZONE, "forbidden")
                self._apply_item_color(item, color)
                self.create_color_button(item)

    def create_toggle_button(self, parent_item):
        """親ノード用のアイコンボタンを作成"""
        toggle_button = QtWidgets.QPushButton()
        toggle_button.setFlat(True)  # フラットスタイル
        toggle_button.setMaximumSize(24, 24)  # ボタンのサイズを制限
        toggle_button.setIconSize(QtCore.QSize(20, 20))  # アイコンサイズ

        # 初期アイコンを設定（デフォルトは全可視）
        self.update_toggle_button_icon(toggle_button, True)

        # クリックイベントを接続
        toggle_button.clicked.connect(
            lambda checked, btn=toggle_button, it=parent_item: self.toggle_all_children(
                btn, it
            )
        )
        # 親ノードのトグルは3列目に配置
        self.tree_widget.setItemWidget(parent_item, 2, toggle_button)

    def create_color_button(self, item):
        """葉ノード用のカラーパレットボタンを作成"""
        color_button = QtWidgets.QPushButton()
        color_button.setFlat(True)
        color_button.setFixedSize(15, 15)
        color_button.clicked.connect(
            lambda checked=False, it=item: self.on_color_button_clicked(it)
        )

        # カラーは2列目に配置
        self.tree_widget.setItemWidget(item, 1, color_button)

        # 併せて落下域切替ボタンを作成（〇/×）
        self.create_zone_button(item)

        color = item.data(0, ROLE_COLOR)
        if isinstance(color, QtGui.QColor):
            self._update_color_button_appearance(color_button, color)

    def on_color_button_clicked(self, item):
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

    def _update_color_button_appearance(self, button: QtWidgets.QPushButton, color):
        button.setStyleSheet(
            "QPushButton {"
            f"background-color: {color.name()};"
            "border: 1px solid #666;"
            "padding: 0px;"
            "}"
        )

    def create_zone_button(self, item: QTreeWidgetItem):
        """葉ノード用の落下域切替ボタン（〇/×）を作成"""
        btn = QtWidgets.QPushButton()
        btn.setFlat(True)
        btn.setCheckable(True)
        btn.setFixedSize(28, 20)

        # 内部データに基づき初期状態を設定
        zone = item.data(0, ROLE_ZONE)
        # デフォルトは 'forbidden' (= ×)
        if zone is None:
            zone = "forbidden"
            item.setData(0, ROLE_ZONE, zone)

        def _apply_zone_appearance(b: QtWidgets.QPushButton, z):
            if z == "allowed":
                b.setChecked(True)
                b.setText("〇")
                b.setStyleSheet("QPushButton { color: green; font-weight: bold; }")
            else:
                b.setChecked(False)
                b.setText("×")
                b.setStyleSheet("QPushButton { color: red; font-weight: bold; }")

        _apply_zone_appearance(btn, zone)

        def _on_zone_toggled(checked, it=item, b=btn):
            new_zone = "allowed" if checked else "forbidden"
            it.setData(0, ROLE_ZONE, new_zone)
            _apply_zone_appearance(b, new_zone)

        btn.toggled.connect(_on_zone_toggled)

        # 3列目に配置
        self.tree_widget.setItemWidget(item, 2, btn)

    def _generate_random_color(self) -> QtGui.QColor:
        hue = random.randint(0, 359)
        saturation = random.randint(150, 255)
        value = random.randint(180, 255)
        return QtGui.QColor.fromHsv(hue, saturation, value)

    def _apply_item_color(self, item: QTreeWidgetItem, color: QtGui.QColor):
        if item.data(0, ROLE_VISIBLE):
            base_text_color = QtGui.QColor(QtCore.Qt.GlobalColor.black)
            item.setForeground(0, QtGui.QBrush(base_text_color))
            item.setBackground(0, QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))

    def update_toggle_button_icon(self, button, all_visible):
        """ボタンのアイコンを更新"""
        if all_visible:
            button.setIcon(self.visible_icon)
        else:
            button.setIcon(self.invisible_icon)

    def on_item_clicked(self, item, column):
        # 葉ノードのみ処理
        if item.childCount() == 0:
            visible = item.data(0, ROLE_VISIBLE)
            if visible is None:
                visible = True
            visible = not visible
            item.setData(0, ROLE_VISIBLE, visible)
            # 色変更
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

    def toggle_all_children(self, button, parent_item):
        """親ノード配下のすべての葉ノードの可視状態を一括で切り替える"""
        # すべての子孫葉ノードの可視状態を取得
        leaf_nodes = self.get_all_leaf_nodes(parent_item)
        if not leaf_nodes:
            return

        # すべて可視かどうかをチェック
        all_visible = all(node.data(0, ROLE_VISIBLE) for node in leaf_nodes)

        # すべて可視なら全部非可視に、そうでなければ全部可視に
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

        # ボタンのアイコンを更新
        self.update_toggle_button_icon(button, new_state)

    def get_all_leaf_nodes(self, parent_item):
        """指定されたアイテム配下のすべての葉ノードを取得"""
        leaf_nodes = []

        def traverse(item):
            if item.childCount() == 0:
                # 葉ノード
                leaf_nodes.append(item)
            else:
                # 子ノードを再帰的に探索
                for i in range(item.childCount()):
                    traverse(item.child(i))

        traverse(parent_item)
        return leaf_nodes
