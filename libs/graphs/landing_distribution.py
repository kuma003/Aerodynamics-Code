from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pyqtgraph as pg

from .base import GraphBase


class LandingDistributionGraph(GraphBase):
    def __init__(
        self,
        *,
        width: int,
        height: int,
        parent=None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self._rng = rng or np.random.default_rng()
        self._site_marker: Optional[pg.PlotDataItem] = None
        super().__init__(name="着地予測散布", width=width, height=height, parent=parent)

    def _initialize_plot(self) -> None:
        theta = np.linspace(0, 2 * math.pi, 80, endpoint=False)
        radius = 0.75 + 0.1 * self._rng.random(theta.size)
        x_vals = radius * np.cos(theta)
        y_vals = radius * np.sin(theta)
        self.plot_widget.plot(
            x_vals,
            y_vals,
            pen=None,
            symbol="o",
            symbolPen=pg.mkPen(color="#0277bd"),
            symbolSize=7,
            symbolBrush=pg.mkBrush("#4fc3f7"),
            name="シミュ散布",
        )

        self._site_marker = self.plot_widget.plot(
            [],
            [],
            pen=None,
            symbol="star",
            symbolSize=16,
            symbolBrush=pg.mkBrush("#d32f2f"),
            symbolPen=pg.mkPen("#b71c1c", width=1.5),
            name="射場",
        )

        self.plot_widget.addLegend(offset=(10, 10))
        self.plot_widget.setLabel("bottom", "東西偏差", units="km")
        self.plot_widget.setLabel("left", "南北偏差", units="km")
        self.plot_widget.setTitle("着地予測散布", color="#01579b")
        self.lock_viewbox_aspect(
            x_range=(-1.2, 1.2),
            y_range=(-1.2, 1.2),
            ratio=1.0,
        )

    def update_site_coordinate(self, coord: Optional[tuple[float, float]]) -> None:
        if self._site_marker is None:
            return
        if coord is None:
            self._site_marker.setData([], [])
            self._site_marker.setToolTip("")
        else:
            lat, lon = coord
            self._site_marker.setData([0.0], [0.0])
            self._site_marker.setToolTip(f"緯度: {lat:.5f}\n経度: {lon:.5f}")
