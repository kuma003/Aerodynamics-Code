from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tomllib
from pyqtgraph.Qt import QtWidgets

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

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._map_entries: list[MapTileEntry] = []
        self._map_file_path: Path = self.CONFIG_PATH
        self._build_ui()
        self._load_map_file()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(create_section_title("地図設定"))

        form_widget = create_form_widget()
        form_layout = form_widget.layout()

        self.map_combo = QtWidgets.QComboBox()
        self.map_combo.currentIndexChanged.connect(self._on_map_selected)
        form_layout.addRow("地図:", self.map_combo)

        self.min_zoom_label = QtWidgets.QLabel("-")
        self.min_zoom_label.setFixedHeight(20)
        form_layout.addRow("最小ズーム:", self.min_zoom_label)

        self.max_zoom_label = QtWidgets.QLabel("-")
        self.max_zoom_label.setFixedHeight(20)
        form_layout.addRow("最大ズーム:", self.max_zoom_label)

        self.zoom_spin = QtWidgets.QSpinBox()
        self.zoom_spin.setRange(0, 25)
        self.zoom_spin.valueChanged.connect(self._on_zoom_value_changed)
        form_layout.addRow("ズームレベル:", self.zoom_spin)

        self.attribution_edit = QtWidgets.QPlainTextEdit()
        self.attribution_edit.setPlaceholderText("著作権表示を入力")
        self.attribution_edit.setFixedHeight(60)
        self.attribution_edit.textChanged.connect(self._on_attribution_text_changed)
        form_layout.addRow("Attribution:", self.attribution_edit)

        layout.addWidget(form_widget)

        layout.addWidget(create_section_title("内部計算座標系"))

        layout.addStretch()

        self._set_controls_enabled(False)

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
