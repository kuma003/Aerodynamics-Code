from pyqtgraph.Qt import QtCore, QtWidgets


def create_section_title(text: str) -> QtWidgets.QLabel:
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
