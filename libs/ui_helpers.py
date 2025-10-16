from pyqtgraph.Qt import QtCore, QtWidgets


def create_section_title(text: str) -> QtWidgets.QGroupBox:
    group = QtWidgets.QGroupBox(text)
    layout = QtWidgets.QVBoxLayout()
    layout.setContentsMargins(12, 6, 12, 12)
    layout.setSpacing(6)
    group.setLayout(layout)
    return group


def create_form_widget() -> QtWidgets.QWidget:
    widget = QtWidgets.QWidget()
    form_layout = QtWidgets.QFormLayout()
    form_layout.setLabelAlignment(
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    widget.setLayout(form_layout)
    return widget


def add_separator(
    layout: QtWidgets.QLayout, top_bottom_margin: int = 4
) -> QtWidgets.QFrame:
    container = QtWidgets.QWidget()
    container_layout = QtWidgets.QVBoxLayout(container)
    container_layout.setContentsMargins(0, top_bottom_margin, 0, top_bottom_margin)
    container_layout.setSpacing(0)

    separator = QtWidgets.QFrame()
    separator.setLineWidth(1)
    layout.addWidget(container)
    return separator
