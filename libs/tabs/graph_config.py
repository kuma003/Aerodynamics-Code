from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tomllib
from pyqtgraph.Qt import QtCore, QtWidgets

from ..crs_utils import *
from ..ui_helpers import create_form_widget, create_section_title


@dataclass
class MapTileEntry:
    table: dict[str, Any]
    key_order: list[str]

    def display_name(self) -> str:
        name = self.table.get("name")
        if isinstance(name, str) and name:
            return name
        name_en = self.table.get("name.en")
        if isinstance(name_en, str) and name_en:
            return name_en
        return "Unnamed Map"


class GraphConfigTab(QtWidgets.QWidget):
    CONFIG_PATH = (
        Path(__file__).resolve().parent.parent.parent / "configs" / "maptile.toml"
    )

    graph_settings_changed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._map_entries: list[MapTileEntry] = []
        self._map_file_path: Path = self.CONFIG_PATH
        self._gcs_entries: list[GCS] = []
        self._projected_entries: list[ProjectedCRS] = []
        self._current_proj_variants: list[ProjectedCRSVariant] = []
        self._crs_ready = False
        self._site_coord = DEFAULT_SITE_COORD
        self._build_ui()
        self._load_crs_data()
        self._load_map_file()
        self._emit_graph_settings_changed()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        graph_section = create_section_title("グラフ設定")
        layout.addWidget(graph_section)

        self.graph_form_widget = create_form_widget()
        graph_section.layout().addWidget(self.graph_form_widget)
        self.graph_form_layout = self.graph_form_widget.layout()

        self.graph_width_spin = QtWidgets.QSpinBox(minimum=100, maximum=10000)
        self.graph_height_spin = QtWidgets.QSpinBox(minimum=100, maximum=10000)
        self.graph_width_spin.setValue(800)
        self.graph_height_spin.setValue(600)
        self.graph_width_spin.valueChanged.connect(self._emit_graph_settings_changed)
        self.graph_height_spin.valueChanged.connect(self._emit_graph_settings_changed)
        self.graph_form_layout.addRow("横幅:", self.graph_width_spin)
        self.graph_form_layout.addRow("高さ:", self.graph_height_spin)

        self.graph_export_dpi_spin = QtWidgets.QSpinBox(value=96)
        self.graph_export_dpi_spin.setRange(36, 600)
        self.graph_export_dpi_spin.valueChanged.connect(
            self._emit_graph_settings_changed
        )
        self.graph_form_layout.addRow("DPI:", self.graph_export_dpi_spin)

        self.graph_export_format_combo = QtWidgets.QComboBox()
        self.graph_export_format_combo.addItems(["PNG", "SVG", "PDF"])
        self.graph_export_format_combo.currentIndexChanged.connect(
            self._emit_graph_settings_changed
        )
        self.graph_form_layout.addRow("出力形式:", self.graph_export_format_combo)

        map_section = create_section_title("地図設定")
        layout.addWidget(map_section)

        self.map_form_widget = create_form_widget()
        map_section.layout().addWidget(self.map_form_widget)
        self.map_form_layout = self.map_form_widget.layout()

        self.map_combo = QtWidgets.QComboBox()
        self.map_combo.currentIndexChanged.connect(self._on_map_selected)
        self.map_form_layout.addRow("地図:", self.map_combo)

        self.min_zoom_label = QtWidgets.QLabel("-")
        self.min_zoom_label.setFixedHeight(20)
        self.map_form_layout.addRow("最小ズーム:", self.min_zoom_label)

        self.max_zoom_label = QtWidgets.QLabel("-")
        self.max_zoom_label.setFixedHeight(20)
        self.map_form_layout.addRow("最大ズーム:", self.max_zoom_label)

        self.zoom_spin = QtWidgets.QSpinBox()
        self.zoom_spin.setRange(0, 25)
        self.zoom_spin.valueChanged.connect(self._on_zoom_value_changed)
        self.map_form_layout.addRow("ズームレベル:", self.zoom_spin)

        self.attribution_edit = QtWidgets.QPlainTextEdit()
        self.attribution_edit.setPlaceholderText("著作権表示を入力")
        self.attribution_edit.setMaximumHeight(80)
        self.attribution_edit.sizePolicy().setVerticalStretch(0)
        self.attribution_edit.textChanged.connect(self._on_attribution_text_changed)
        self.map_form_layout.addRow("Attribution:", self.attribution_edit)

        crs_section = create_section_title("参照座標系")
        layout.addWidget(crs_section)

        self.crs_form_widget = create_form_widget()
        crs_section.layout().addWidget(self.crs_form_widget)
        self.crs_form_layout = self.crs_form_widget.layout()

        self.gcs_combo = QtWidgets.QComboBox()
        self.crs_form_layout.addRow("地理座標系:", self.gcs_combo)

        self.proj_group_combo = QtWidgets.QComboBox()
        self.proj_group_combo.currentIndexChanged.connect(self._on_proj_group_changed)
        self.crs_form_layout.addRow("投影座標系:", self.proj_group_combo)

        self.proj_variant_combo = QtWidgets.QComboBox()
        self.proj_variant_combo.currentIndexChanged.connect(
            self._on_proj_variant_changed
        )

        self.auto_variant_check = QtWidgets.QCheckBox("射場座標から自動選択")
        self.auto_variant_check.setChecked(True)
        self.auto_variant_check.toggled.connect(self._on_auto_variant_toggled)

        variant_row = QtWidgets.QWidget()
        variant_layout = QtWidgets.QHBoxLayout()
        variant_layout.setContentsMargins(0, 0, 0, 0)
        variant_layout.setSpacing(8)
        variant_layout.addWidget(self.proj_variant_combo, 1)
        variant_layout.addWidget(self.auto_variant_check)
        variant_row.setLayout(variant_layout)
        self.crs_form_layout.addRow("系/帯:", variant_row)

        layout.addStretch()

        self._set_controls_enabled(False)
        self._update_crs_widget_states()

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.map_combo.setEnabled(enabled)
        self.zoom_spin.setEnabled(enabled)
        self.attribution_edit.setEnabled(enabled)

    def _load_map_file(self) -> None:
        path = self._map_file_path

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "エラー",
                f"設定ファイルを開けませんでした:\n{exc}",
            )
            self._set_controls_enabled(False)
            return

        try:
            data = tomllib.loads("".join(text))
        except tomllib.TOMLDecodeError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "エラー",
                f"設定ファイルの解析に失敗しました:\n{exc}",
            )
            self._set_controls_enabled(False)
            return

        tables_raw = data.get("maptile")
        if isinstance(tables_raw, dict):
            map_tables = [tables_raw]
        elif isinstance(tables_raw, list):
            map_tables = [table for table in tables_raw if isinstance(table, dict)]
        else:
            map_tables = []

        if not map_tables:
            QtWidgets.QMessageBox.warning(
                self,
                "情報",
                "[maptile] セクションが見つかりませんでした。",
            )
            self._set_controls_enabled(False)
            return

        self._map_entries = [
            MapTileEntry(table=dict(table), key_order=list(table.keys()))
            for table in map_tables
        ]

        self._set_controls_enabled(True)
        self._refresh_map_combo()

    def _refresh_map_combo(self) -> None:
        self.map_combo.blockSignals(True)
        self.map_combo.clear()
        for entry in self._map_entries:
            self.map_combo.addItem(entry.display_name(), entry)
        self.map_combo.blockSignals(False)
        if self._map_entries:
            self.map_combo.setCurrentIndex(0)
            self._populate_fields(self._map_entries[0])
        else:
            self._set_controls_enabled(False)

    def _populate_fields(self, entry: MapTileEntry) -> None:
        self._set_controls_enabled(True)
        self.zoom_spin.blockSignals(True)
        self.attribution_edit.blockSignals(True)

        min_zoom = entry.table.get("min_zoom")
        if not isinstance(min_zoom, int):
            min_zoom = 0
        max_zoom = entry.table.get("max_zoom")
        if not isinstance(max_zoom, int):
            max_zoom = 0
        attribution = entry.table.get("attribution")
        if not isinstance(attribution, str):
            attribution = ""

        if max_zoom < min_zoom:
            max_zoom = min_zoom

        self.min_zoom_label.setText(str(min_zoom))
        self.max_zoom_label.setText(str(max_zoom))

        self.zoom_spin.setRange(min_zoom, max_zoom)

        zoom_value = entry.table.get("zoom")
        if not isinstance(zoom_value, int):
            zoom_value = min_zoom

        clamped_zoom = max(min_zoom, min(max_zoom, zoom_value))

        self.zoom_spin.setValue(clamped_zoom)
        self.attribution_edit.setPlainText(attribution)

        self.zoom_spin.blockSignals(False)
        self.attribution_edit.blockSignals(False)

    def _on_map_selected(self, index: int) -> None:
        if 0 <= index < len(self._map_entries):
            self._populate_fields(self._map_entries[index])

    def _on_zoom_value_changed(self, _value: int) -> None:
        if self.zoom_spin.signalsBlocked():
            return

        entry = self._current_entry()
        if entry is None:
            return

        min_zoom = entry.table.get("min_zoom")
        max_zoom = entry.table.get("max_zoom")
        if not isinstance(min_zoom, int):
            min_zoom = 0
        if not isinstance(max_zoom, int):
            max_zoom = min_zoom

        value = self.zoom_spin.value()
        clamped = max(min_zoom, min(max_zoom, value))
        if clamped != value:
            self.zoom_spin.blockSignals(True)
            self.zoom_spin.setValue(clamped)
            self.zoom_spin.blockSignals(False)

        entry.table["zoom"] = clamped

    def _on_attribution_text_changed(self) -> None:
        if self.attribution_edit.signalsBlocked():
            return

        entry = self._current_entry()
        if entry is None:
            return

        entry.table["attribution"] = self.attribution_edit.toPlainText().strip()

    def _current_entry(self) -> Optional[MapTileEntry]:
        index = self.map_combo.currentIndex()
        if 0 <= index < len(self._map_entries):
            return self._map_entries[index]
        return None

    def graph_dimensions(self) -> tuple[int, int]:
        return self.graph_width_spin.value(), self.graph_height_spin.value()

    def graph_dpi(self) -> int:
        return self.graph_export_dpi_spin.value()

    def graph_format(self) -> str:
        return self.graph_export_format_combo.currentText().strip().lower()

    def _emit_graph_settings_changed(self) -> None:
        # Emit a consolidated signal so consumers can react to any relevant change.
        self.graph_settings_changed.emit()

    def _load_crs_data(self) -> None:
        try:
            catalog = load_crs_catalog()
        except CRSCatalogError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "エラー",
                f"CRS設定の読み込みに失敗しました:\n{exc}",
            )
            self._crs_ready = False
            self._gcs_entries.clear()
            self._projected_entries.clear()
            self._current_proj_variants = []
            self._update_crs_widget_states()
            return

        self._gcs_entries = list(catalog.gcs)
        self._projected_entries = list(catalog.projected)
        self._crs_ready = True

        self._populate_gcs_combo()
        self._populate_proj_group_combo()
        self._set_initial_gcs_selection()
        self._set_initial_projected_selection()
        self._update_crs_widget_states()

    def _populate_gcs_combo(self) -> None:
        self.gcs_combo.blockSignals(True)
        self.gcs_combo.clear()
        for entry in self._gcs_entries:
            self.gcs_combo.addItem(entry.display_label(), entry)
        self.gcs_combo.blockSignals(False)
        if self._gcs_entries:
            self.gcs_combo.setCurrentIndex(0)

    def _populate_proj_group_combo(self) -> None:
        self.proj_group_combo.blockSignals(True)
        self.proj_group_combo.clear()
        for group in self._projected_entries:
            self.proj_group_combo.addItem(group.display_label(), group)
        self.proj_group_combo.blockSignals(False)

        if self._projected_entries:
            self.proj_group_combo.setCurrentIndex(0)
            self._populate_proj_variant_combo(0)
        else:
            self._populate_proj_variant_combo(-1)

    def _populate_proj_variant_combo(
        self,
        group_index: int,
        *,
        preferred: ProjectedCRSVariant | None = None,
    ) -> None:
        self._current_proj_variants = []
        self.proj_variant_combo.blockSignals(True)
        self.proj_variant_combo.clear()

        if not (0 <= group_index < len(self._projected_entries)):
            self.proj_variant_combo.blockSignals(False)
            return

        variants = list(self._projected_entries[group_index].variants)
        self._current_proj_variants = variants

        for variant in variants:
            self.proj_variant_combo.addItem(variant.display_label(), variant)

        if preferred and preferred in variants:
            self.proj_variant_combo.setCurrentIndex(variants.index(preferred))
        elif variants:
            self.proj_variant_combo.setCurrentIndex(0)

        self.proj_variant_combo.blockSignals(False)

    def _set_initial_gcs_selection(self) -> None:
        if not self._gcs_entries:
            return
        suggested = choose_geographic_crs(self._gcs_entries)
        try:
            index = self._gcs_entries.index(suggested) if suggested else 0
        except ValueError:
            index = 0
        self._set_combo_index(self.gcs_combo, index)

    def _set_initial_projected_selection(self) -> None:
        if not self._projected_entries:
            self._populate_proj_variant_combo(-1)
            return

        selection = choose_projected_group(self._projected_entries, self._site_coord)
        if selection is None:
            self._set_combo_index(self.proj_group_combo, 0)
            if self.auto_variant_check.isChecked():
                self._apply_auto_variant_selection(0)
            else:
                self._populate_proj_variant_combo(0)
            return

        group, variant = selection
        try:
            group_index = self._projected_entries.index(group)
        except ValueError:
            group_index = 0

        self._set_combo_index(self.proj_group_combo, group_index)
        if self.auto_variant_check.isChecked():
            self._apply_auto_variant_selection(group_index)
        else:
            self._populate_proj_variant_combo(group_index, preferred=variant)

    def _apply_auto_variant_selection(self, group_index: Optional[int] = None) -> None:
        if group_index is None:
            group_index = self.proj_group_combo.currentIndex()

        if not (0 <= group_index < len(self._projected_entries)):
            self._populate_proj_variant_combo(-1)
            return

        group = self._projected_entries[group_index]
        preferred = group.best_variant_for_coordinate(self._site_coord)
        self._populate_proj_variant_combo(group_index, preferred=preferred)

    def set_site_coordinate(self, coord: Optional[tuple[float, float]]) -> None:
        self._site_coord = coord if coord is not None else DEFAULT_SITE_COORD
        if not self._crs_ready:
            return
        if self.auto_variant_check.isChecked():
            self._apply_auto_variant_selection()
        self._update_crs_widget_states()

    def _set_combo_index(self, combo: QtWidgets.QComboBox, index: int) -> None:
        if index < 0 or index >= combo.count():
            return
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _on_auto_variant_toggled(self, checked: bool) -> None:
        if self._crs_ready and checked:
            self._apply_auto_variant_selection()
        self._update_crs_widget_states()

    def _on_proj_group_changed(self, index: int) -> None:
        if not self._crs_ready:
            return

        if self.auto_variant_check.isChecked():
            self._apply_auto_variant_selection(index)
        else:
            self._populate_proj_variant_combo(index)
        self._update_crs_widget_states()

    def _on_proj_variant_changed(self, _index: int) -> None:
        if self.auto_variant_check.isChecked():
            return
        # Manual selection requires no immediate action yet, but we keep the handler
        # for future integration (e.g., persisting settings).

    def _update_crs_widget_states(self) -> None:
        has_gcs = bool(self._gcs_entries)
        has_proj = bool(self._projected_entries)
        has_variants = bool(self._current_proj_variants)
        ready = self._crs_ready

        self.gcs_combo.setEnabled(ready and has_gcs)
        self.proj_group_combo.setEnabled(ready and has_proj)

        auto_available = ready and has_proj and has_variants
        if ready and not auto_available and self.auto_variant_check.isChecked():
            self.auto_variant_check.blockSignals(True)
            self.auto_variant_check.setChecked(False)
            self.auto_variant_check.blockSignals(False)

        self.auto_variant_check.setEnabled(auto_available)

        manual_variant_enabled = (
            ready
            and has_proj
            and has_variants
            and not self.auto_variant_check.isChecked()
        )
