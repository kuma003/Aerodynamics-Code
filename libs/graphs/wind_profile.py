from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from .base import GraphBase


class WindProfileGraph(GraphBase):
    def __init__(self, *, width: int, height: int, parent=None) -> None:
        super().__init__(name="風速プロファイル", width=width, height=height, parent=parent)

    def _initialize_plot(self) -> None:
        altitude = np.linspace(0, 3000, 40)
        base_speed = 5 + 3 * np.cos(altitude / 800)
        gust_component = 0.8 * np.sin(altitude / 120)
        speed = base_speed + gust_component
        self.plot_widget.plot(speed, altitude, pen=pg.mkPen("#388e3c", width=2))
        self.plot_widget.setLabel("bottom", "風速", units="m/s")
        self.plot_widget.setLabel("left", "高度", units="m")
        self.plot_widget.setTitle("推定風速プロファイル", color="#1b5e20")
        speed_min = float(speed.min())
        speed_max = float(speed.max())
        x_span = speed_max - speed_min
        padding = 0.05 * x_span if x_span else 2.0
        self.lock_viewbox_aspect(
            x_range=(speed_min - padding, speed_max + padding),
            y_range=(float(altitude.min()), float(altitude.max())),
        )
