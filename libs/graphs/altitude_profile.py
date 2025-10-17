from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from .base import GraphBase


class AltitudeProfileGraph(GraphBase):
    def __init__(self, *, width: int, height: int, parent=None) -> None:
        super().__init__(name="高度プロファイル", width=width, height=height, parent=parent)

    def _initialize_plot(self) -> None:
        time_s = np.linspace(0, 180, 200)
        altitude_m = 1500 * np.exp(-time_s / 120) + 100 * np.sin(time_s / 8)
        self.plot_widget.plot(time_s, altitude_m, pen=pg.mkPen("#1976d2", width=2))
        self.plot_widget.setLabel("bottom", "時間", units="s")
        self.plot_widget.setLabel("left", "高度", units="m")
        self.plot_widget.setTitle("模擬高度プロファイル", color="#0d47a1")
        altitude_min = float(altitude_m.min())
        altitude_max = float(altitude_m.max())
        y_span = altitude_max - altitude_min
        padding = 0.05 * y_span if y_span else 10.0
        self.lock_viewbox_aspect(
            x_range=(float(time_s.min()), float(time_s.max())),
            y_range=(altitude_min - padding, altitude_max + padding),
        )
