import numpy as np
import pyqtgraph as pg
import os

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor

from visualizer.engine import recompute


# ---------------- PAN PLOT WIDGET ----------------

class PanPlotWidget(pg.PlotWidget):
    def __init__(self, on_pan):
        super().__init__()
        self.on_pan = on_pan
        self._panning = False
        self._last_pos = None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pos = ev.position()
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._panning and self._last_pos is not None:
            delta = ev.position() - self._last_pos
            self._last_pos = ev.position()

            vb = self.plotItem.vb
            if vb is None:
                return

            xr = vb.viewRange()[0]
            yr = vb.viewRange()[1]

            # FIXED direction (no inversion mismatch)
            dx = delta.x() * (xr[1] - xr[0]) / self.width()
            dy = -delta.y() * (yr[1] - yr[0]) / self.height()

            self.on_pan(dx, dy)

            ev.accept()
            return

        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._last_pos = None
            ev.accept()
            return
        super().mouseReleaseEvent(ev)


# ---------------- DRAG FIELD ----------------

class DragField(QtWidgets.QWidget):
    def __init__(self, label, value, on_change):
        super().__init__()

        self.value = float(value)
        self.on_change = on_change

        self.dragging = False
        self.last_x = 0

        self.label_text = label
        self.label = QtWidgets.QLabel()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.label)
        self.setLayout(layout)

        self.setFixedHeight(22)

        self._update_label()

    def _update_label(self):
        self.label.setText(f"{self.label_text}: {self.value:.6f}")

    def set_value(self, v):
        self.value = float(v)
        self._update_label()

    def mousePressEvent(self, event):
        self.dragging = True
        self.last_x = event.position().x()

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return

        dx = event.position().x() - self.last_x
        self.last_x = event.position().x()

        modifiers = event.modifiers()

        scale = 1.0
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            scale = 500.0
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            scale = 0.1

        self.value += dx * scale
        self._update_label()
        self.on_change(self.value)

    def mouseReleaseEvent(self, event):
        self.dragging = False


# ---------------- DATASET UI ----------------

class DatasetUI:
    def __init__(self, dataset, color, toolbox, on_change):
        self.ds = dataset
        self.toolbox = toolbox
        self.on_change = on_change

        self.page = QtWidgets.QWidget()

        self.page.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum
        )

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.page.setLayout(self.layout)

        self.idx = toolbox.addItem(self.page, os.path.basename(dataset.filename))
        toolbox.setItemIcon(self.idx, self._icon(color))
        toolbox.setItemToolTip(self.idx, dataset.filename)

        self.sliders = {}
        self.labels = {}

        self._build_ui()

    def _icon(self, color_hex):
        pix = QPixmap(14, 14)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 10, 10)
        painter.end()

        return QIcon(pix)

    def _mk_slider(self, name, minv, maxv, value):
        container = QtWidgets.QWidget()
        container.setFixedHeight(46)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl = QtWidgets.QLabel()
        lbl.setFixedHeight(16)

        s = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        s.setRange(minv, maxv)
        s.setFixedHeight(18)

        if name == "Trim end":
            s.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        def update(val):
            lbl.setText(f"{name}: {val}")
            self._apply_slider(name, val)
            self.on_change()

        s.valueChanged.connect(update)

        self.sliders[name] = s
        self.labels[name] = lbl

        layout.addWidget(lbl)
        layout.addWidget(s)

        container.setLayout(layout)

        self.set_slider(name, value)

        return container

    def set_slider(self, name, value):
        if name not in self.sliders:
            return

        s = self.sliders[name]
        lbl = self.labels[name]

        s.blockSignals(True)
        s.setValue(int(value))
        s.blockSignals(False)

        lbl.setText(f"{name}: {value}")

    def sync_offsets(self):
        self.x_drag.set_value(self.ds.x_offset)
        self.y_drag.set_value(self.ds.y_offset)

    def sync_from_dataset(self):
        d = self.ds
        self.set_slider("Trim start", d.start_trim)
        self.set_slider("Trim end", d.end_trim)
        self.set_slider("Roll", d.roll)

    def _apply_slider(self, name, value):
        if name == "Trim start":
            self.ds.start_trim = value
        elif name == "Trim end":
            self.ds.end_trim = value
        elif name == "Roll":
            self.ds.roll = value

    def _build_ui(self):
        d = self.ds

        self.layout.addWidget(self._mk_slider("Trim start", 0, 10000, d.start_trim))
        self.layout.addWidget(self._mk_slider("Trim end", 0, 10000, d.end_trim))

        self.x_drag = DragField(
            "X offset",
            d.x_offset,
            lambda v: (setattr(self.ds, "x_offset", v), self.on_change())
        )

        self.y_drag = DragField(
            "Y offset",
            d.y_offset,
            lambda v: (setattr(self.ds, "y_offset", v), self.on_change())
        )

        self.layout.addWidget(self.x_drag)
        self.layout.addWidget(self.y_drag)

        self.layout.addWidget(self._mk_slider("Roll", 1, 400, d.roll))

    def remove(self):
        self.toolbox.removeItem(self.idx)
        self.page.deleteLater()


# ---------------- MAIN WINDOW ----------------

class MainWindow(QtWidgets.QWidget):
    def __init__(self, colors, factory):
        super().__init__()

        self.datasets = []
        self.colors = colors
        self.factory = factory
        self.ui_map = {}

        self.setWindowTitle("Dataset Tool")

        self.plot_widget = PanPlotWidget(self._apply_pan)
        self.plot = self.plot_widget.plotItem
        self.plot.showGrid(True, True)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumWidth(280)

        self.container = QtWidgets.QWidget()
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container.setLayout(self.vbox)

        self.scroll.setWidget(self.container)

        self.toolbox = QtWidgets.QToolBox()
        self.vbox.addWidget(self.toolbox)

        self.btn_add = QtWidgets.QPushButton("Add Dataset")
        self.btn_remove = QtWidgets.QPushButton("Remove Dataset")

        self.vbox.addWidget(self.btn_add)
        self.vbox.addWidget(self.btn_remove)

        self.btn_add.clicked.connect(self.add_dataset)
        self.btn_remove.clicked.connect(self.remove_dataset)

        self.splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.plot_widget)
        self.splitter.addWidget(self.scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([1200, 400])

        root = QtWidgets.QVBoxLayout()
        root.addWidget(self.splitter)
        self.setLayout(root)

        self.redraw()

    def _apply_pan(self, dx, dy):
        idx = self.toolbox.currentIndex()
        if idx < 0:
            return

        widget = self.toolbox.widget(idx)

        ds = next(
            (d for d in self.datasets if self.ui_map[d.id].page is widget),
            None
        )

        if ds is None:
            return

        ds.x_offset += dx
        ds.y_offset += dy

        # sync UI to dataset (critical fix)
        ui = self.ui_map.get(ds.id)
        if ui:
            ui.sync_offsets()

        self.redraw()

    def _add_ui(self, ds, color):
        ui = DatasetUI(ds, color, self.toolbox, self.redraw)
        self.ui_map[ds.id] = ui

    def add_dataset(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add CSV", "", "CSV (*.csv)"
        )
        if not paths:
            return

        for p in paths:
            ds = self.factory.create(p)
            ds.color = self.colors[len(self.datasets) % len(self.colors)]
            self.datasets.append(ds)
            self._add_ui(ds, ds.color)

        self.toolbox.setCurrentIndex(self.toolbox.count() - 1)

        self.redraw()

    def remove_dataset(self):
        idx = self.toolbox.currentIndex()
        if idx < 0:
            return

        widget = self.toolbox.widget(idx)

        ds = next(
            (d for d in self.datasets if self.ui_map[d.id].page is widget),
            None
        )
        if ds is None:
            return

        ui = self.ui_map.pop(ds.id, None)
        if ui:
            ui.remove()

        self.datasets = [d for d in self.datasets if d.id != ds.id]
        self.redraw()

    def redraw(self):
        for i, ds in enumerate(self.datasets):

            if ds.color is None:
                ds.color = self.colors[i % len(self.colors)]

            if not hasattr(ds, "curve") or ds.curve is None:
                ds.curve = self.plot.plot(pen=pg.mkPen(ds.color, width=2))

            df = recompute(ds)
            if df is None:
                continue

            ds.curve.setData(
                df["t"].to_numpy() + ds.x_offset,
                df["v"].to_numpy() + ds.y_offset
            )

    def load_project(self, project):
        for ds in self.datasets:
            cfg = project.get("datasets", {}).get(ds.id)
            if cfg:
                ds.apply_dict(cfg)

        for ds in self.datasets:
            ui = self.ui_map.get(ds.id)
            if ui:
                ui.sync_from_dataset()

        self.redraw()

    def rebuild_from_project(self, project):
        self.datasets.clear()
        self.ui_map.clear()

        while self.toolbox.count() > 0:
            w = self.toolbox.widget(0)
            self.toolbox.removeItem(0)
            if w:
                w.deleteLater()

        self.plot.clear()
        self.factory.file_counter.clear()

        for i, f in enumerate(project.get("files", [])):
            ds = self.factory.create(f)
            ds.color = self.colors[i % len(self.colors)]
            self.datasets.append(ds)
            self._add_ui(ds, ds.color)

        self.load_project(project)
        self.redraw()
