from __future__ import annotations

from typing import Optional

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets


class AspectRatioContainer(QtWidgets.QWidget):
    def __init__(
        self,
        content: QtWidgets.QWidget,
        *,
        width: int = 4,
        height: int = 3,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._content = content
        self._ratio = self._compute_ratio(width, height)
        self._content.setParent(self)
        self._content.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored,
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def set_ratio(self, width: int, height: int) -> None:
        self._ratio = self._compute_ratio(width, height)
        self._relayout()

    @property
    def ratio(self) -> float:
        return self._ratio

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def sizeHint(self) -> QtCore.QSize:
        hint = self._content.sizeHint()
        if self._ratio <= 0:
            return hint
        width = hint.width()
        height = hint.height()
        if height <= 0:
            height = max(1, int(width / self._ratio))
        return QtCore.QSize(width, height)

    @staticmethod
    def _compute_ratio(width: int, height: int) -> float:
        if width <= 0 or height <= 0:
            return 0.0
        return width / height

    def _relayout(self) -> None:
        if not self._content:
            return

        rect = self.rect()
        if rect.isEmpty():
            return

        if self._ratio <= 0:
            self._content.setGeometry(rect)
            return

        available_width = rect.width()
        available_height = rect.height()

        target_width = min(available_width, int(available_height * self._ratio))
        target_height = min(available_height, int(available_width / self._ratio))

        if target_width / max(target_height, 1) > self._ratio:
            target_width = int(target_height * self._ratio)
        else:
            target_height = int(target_width / self._ratio)

        offset_x = rect.x() + (available_width - target_width) // 2
        offset_y = rect.y() + (available_height - target_height) // 2

        self._content.setGeometry(
            QtCore.QRect(offset_x, offset_y, target_width, target_height)
        )


__all__ = ["AspectRatioContainer"]
