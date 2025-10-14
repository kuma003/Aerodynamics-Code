from pyqtgraph.Qt import QtWidgets
from pyqtgraph.Qt.QtCore import QRegularExpression
from pyqtgraph.Qt.QtGui import QRegularExpressionValidator

from ..ui_helpers import add_separator, create_form_widget, create_section_title

float_regex = QRegularExpression(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
float_input_validator = QRegularExpressionValidator(float_regex)


class SimulationTab(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._updating_specific_wind = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(create_section_title("機体諸元ファイル選択"))
        self.airframe_file_combo = QtWidgets.QComboBox()
        self.airframe_file_combo.addItem("選択なし", None)
        layout.addWidget(self.airframe_file_combo)

        add_separator(layout)

        layout.addWidget(create_section_title("シミュレーション条件"))
        self.simulation_config_widget = self._create_simulation_config_widget()
        layout.addWidget(self.simulation_config_widget)

        add_separator(layout)

        layout.addWidget(create_section_title("風条件設定"))
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
        layout.addWidget(self.wind_forms_stack)

        self.simulation_mode_combo.currentIndexChanged.connect(
            self._on_sim_condition_changed
        )
        self._on_sim_condition_changed(0)

        add_separator(layout)

        layout.addWidget(create_section_title("風モデル設定"))
        layout.addWidget(self._create_wind_model_form_widget())

        add_separator(layout)

        layout.addWidget(create_section_title("シミュレーション設定"))
        layout.addWidget(QtWidgets.QPushButton("実行"))
        layout.addStretch()

    def _create_simulation_config_widget(self) -> QtWidgets.QWidget:
        widget = create_form_widget()
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
        widget = create_form_widget()
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
        widget = create_form_widget()
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

    def _create_wind_model_form_widget(self) -> QtWidgets.QWidget:
        widget = create_form_widget()
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

    def _on_sim_condition_changed(self, index: int) -> None:
        mode = self.simulation_mode_combo.itemData(index)
        if mode:
            self._update_simulation_mode(mode)

    def _update_simulation_mode(self, mode: str) -> None:
        if mode == "Scatter":
            self.wind_forms_stack.setCurrentWidget(self.scatter_form_widget)
        else:
            self.wind_forms_stack.setCurrentWidget(self.detail_form_widget)

    def _on_wind_model_changed(self, index: int) -> None:
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

    def _on_specific_wind_selected(self, index: int) -> None:
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
