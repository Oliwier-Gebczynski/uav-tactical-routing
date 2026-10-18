#!/usr/bin/env python3
"""Local map, scenario editor and simulation results application."""
import argparse
import codecs
import copy
from datetime import datetime
import os
from pathlib import Path
import re
import sys
import uuid

os.environ.setdefault("QT_API", "pyqt5")

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Patch

from ..scenarios.model import (MapDocument, PROFILES, new_state, optimizer_profile,
                            scenario_document, state_from_document, validate_state, write_document)

from ..paths import ROOT
COLORS = ["#173d52", "#344b36", "#183c2e", "#202c33", "#7b8c88"]
CYAN, GREEN, AMBER, RED = "#66d9d0", "#b6cd82", "#edbd6e", "#ed7777"
BG, PANEL, TEXT, MUTED = "#0b1216", "#111d23", "#d9e5e4", "#8b9e9e"
RUNS = [("baseline", "Prosta", AMBER), ("pure_ls", "Local Search", "#b5a2df"),
        ("pure_sa", "SA", "#76a5e2"), ("sa_ls", "SA + LS", CYAN)]
STYLE = """
QWidget { background: #0b1216; color: #d9e5e4; font-family: 'DejaVu Sans'; font-size: 12px; }
QMainWindow, QDialog { background: #0b1216; }
QLabel#brand { color: #b6cd82; font-size: 24px; font-weight: 700; letter-spacing: 2px; }
QLabel#eyebrow { color: #66d9d0; font-size: 10px; letter-spacing: 2px; }
QLabel#muted { color: #8b9e9e; }
QLabel#status { color: #b6cd82; padding: 6px 10px; border: 1px solid #344b36; background: #17231b; }
QGroupBox { border: 1px solid #2a3d43; margin-top: 17px; padding: 14px 10px 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #b6cd82; padding: 0 5px; }
QPushButton { background: #1b2c32; border: 1px solid #354b51; padding: 9px 12px; border-radius: 3px; }
QPushButton:hover { background: #283e45; border-color: #66d9d0; }
QPushButton:pressed, QPushButton:checked { background: #284942; border-color: #b6cd82; color: #d9f3ba; }
QPushButton#primary { background: #b6cd82; color: #132018; font-weight: 700; border: 0; }
QPushButton#primary:hover { background: #d0e5a1; }
QPushButton:disabled { background: #152127; color: #52646a; border-color: #22343a; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #101e24; border: 1px solid #34494f; padding: 7px; selection-background-color: #37574b; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #66d9d0; }
QComboBox QAbstractItemView { background: #17272d; selection-background-color: #37574b; }
QTabWidget::pane { border: 1px solid #2a3d43; }
QTabBar::tab { background: #101c22; color: #8b9e9e; padding: 13px 22px; border-bottom: 2px solid #1b2e35; }
QTabBar::tab:selected { background: #17282c; color: #b6cd82; border-bottom: 2px solid #b6cd82; }
QTreeWidget, QTableWidget, QPlainTextEdit { background: #101a20; border: 1px solid #2a3d43; alternate-background-color: #142229; }
QTreeWidget::item { padding: 7px 3px; }
QTreeWidget::item:selected, QTableWidget::item:selected { background: #28453f; }
QHeaderView::section { background: #1a2b31; color: #a7bcba; border: 0; padding: 8px; }
QProgressBar { background: #17272d; border: 0; height: 5px; color: transparent; }
QProgressBar::chunk { background: #b6cd82; }
QSplitter::handle { background: #20343a; }
QToolBar { background: #111d23; border: 0; spacing: 4px; }
QToolButton { background: #21333a; border-radius: 2px; padding: 4px; }
QStatusBar { color: #8b9e9e; }
QScrollArea { border: 0; }
QToolTip { background: #22383e; color: #d9e5e4; border: 1px solid #66d9d0; }
"""


def label(text, kind=None):
    item = QtWidgets.QLabel(text)
    if kind:
        item.setObjectName(kind)
    item.setWordWrap(kind not in {"brand", "eyebrow", "status"})
    return item


def button(text, callback, primary=False):
    item = QtWidgets.QPushButton(text)
    if primary:
        item.setObjectName("primary")
    item.clicked.connect(callback)
    return item


def spin(low, high, value, decimals=0, suffix=""):
    item = QtWidgets.QDoubleSpinBox() if decimals else QtWidgets.QSpinBox()
    item.setRange(low, high)
    if decimals:
        item.setDecimals(decimals)
    item.setValue(value)
    item.setSuffix(suffix)
    item.setKeyboardTracking(False)
    return item


def group(title):
    widget = QtWidgets.QGroupBox(title)
    layout = QtWidgets.QVBoxLayout(widget)
    return widget, layout


def scroll_panel(widget):
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    area.setMinimumWidth(285)
    area.setMaximumWidth(370)
    return area


class Task(QtCore.QThread):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, function, parent):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.succeeded.emit(self.function())
        except Exception as error:
            self.failed.emit(str(error))


class PlotPanel(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(9, 7), facecolor=BG, constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)
        self.axes = None
        self.document = None
        self.canvas.mpl_connect("button_press_event", self._click)
        self.empty("WYBIERZ MAPĘ LUB WYGENERUJ NOWY OBSZAR", "OSM + NMT  /  lokalne pliki JSON")

    def _axes(self, title):
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        ax = self.axes
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=MUTED, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#34494f")
        ax.set_title(title, color=TEXT, fontsize=12, loc="left", pad=14, fontweight="bold")
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        return ax

    def empty(self, title, subtitle):
        ax = self._axes("")
        ax.axis("off")
        ax.text(.5, .54, title, color=GREEN, ha="center", transform=ax.transAxes, fontsize=13, wrap=True)
        ax.text(.5, .46, subtitle, color=MUTED, ha="center", transform=ax.transAxes, fontsize=10, wrap=True)
        self.canvas.draw_idle()

    def _click(self, event):
        if event.button != 1 or event.inaxes is not self.axes or self.document is None or self.toolbar.mode:
            return
        if event.xdata is None or event.ydata is None:
            return
        x, y = int(np.floor(event.xdata + .5)), int(np.floor(event.ydata + .5))
        if 0 <= x < self.document.width and 0 <= y < self.document.height:
            self.clicked.emit(x, y)

    def _colorbar(self, image, title):
        bar = self.figure.colorbar(image, ax=self.axes, fraction=.035, pad=.025, shrink=.82)
        bar.set_label(title, color=MUTED, fontsize=9)
        bar.ax.tick_params(colors=MUTED, labelsize=8)
        bar.outline.set_edgecolor("#34494f")

    def map(self, document, layer="Pokrycie terenu", state=None, paths=None, title=None):
        self.document = document
        ax = self._axes(title or layer.upper())
        extent = (-.5, document.width - .5, document.height - .5, -.5)
        step = max(1, int(np.ceil(max(document.width, document.height) / 900)))
        if layer in {"Pokrycie terenu", "Trasy algorytmów"}:
            ax.imshow(document.terrain[::step, ::step], cmap=ListedColormap(COLORS), vmin=-.5, vmax=4.5,
                      extent=extent, interpolation="nearest")
        else:
            arrays = {"Wysokość gruntu": document.ground, "Wysokość powierzchni": document.surface,
                      "Wysokość przeszkód": document.surface - document.ground, "Pole radarowe": document.threat}
            values = arrays[layer]
            kwargs = {"vmin": 0, "vmax": 1} if layer == "Pole radarowe" else {}
            image = ax.imshow(values[::step, ::step], cmap="magma" if layer == "Pole radarowe" else "terrain",
                              extent=extent, interpolation="nearest", **kwargs)
            self._colorbar(image, "poziom 0–1" if layer == "Pole radarowe" else "m")
        if state:
            for radar in state["radars"]:
                ax.add_patch(Circle((radar["x"], radar["y"]), radar["range"], fill=False, color=RED,
                                    alpha=.55, linewidth=1, linestyle="--"))
                ax.plot(radar["x"], radar["y"], marker="^", color=RED, markersize=9, markeredgecolor=BG)
                ax.annotate(f"R{radar['id']}", (radar["x"], radar["y"]), (7, 7), textcoords="offset points", color=RED, fontsize=8,
                            bbox={"facecolor": BG, "alpha": .8, "edgecolor": "none", "pad": 2})
            points = [(state["start"], "S", GREEN, "o"),
                      *[(point, f"C{i + 1}", AMBER, "D") for i, point in enumerate(state["checkpoints"])],
                      (state["end"], "E", CYAN, "s")]
            route = [point for point, _, _, _ in points if point]
            if route and not paths:
                ax.plot([p["x"] for p in route], [p["y"] for p in route], color=GREEN, alpha=.5, linewidth=1, linestyle=":")
            for point, name, color, marker in points:
                if point:
                    ax.plot(point["x"], point["y"], marker=marker, color=color, markersize=8, markeredgecolor=BG, zorder=5)
                    ax.annotate(name, (point["x"], point["y"]), (8, -12), textcoords="offset points", color=color, fontsize=9,
                                bbox={"facecolor": BG, "alpha": .8, "edgecolor": "none", "pad": 2}, zorder=6)
        handles = []
        if paths:
            for key, name, color in RUNS:
                points = paths.get(key, {}).get("path", [])
                if points:
                    line, = ax.plot([p["x"] for p in points], [p["y"] for p in points], color=color,
                                    linewidth=2 if key == "sa_ls" else 1.2, label=name,
                                    linestyle="-" if key == "sa_ls" else "--", alpha=.95, zorder=4)
                    handles.append(line)
        elif layer == "Pokrycie terenu" and state is None:
            handles = [Patch(color=color, label=name) for color, name in zip(COLORS, ["Woda", "Teren otwarty", "Las", "Droga", "Budynek"])]
        if handles:
            legend = ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=.95, facecolor=PANEL, edgecolor="#34494f")
            for text in legend.get_texts():
                text.set_color(TEXT)
        ax.set_xlim(-.5, document.width - .5)
        ax.set_ylim(document.height - .5, -.5)
        ax.set_xlabel("x / wschód [m]")
        ax.set_ylabel("y / południe [m]")
        ax.text(.98, .98, "N ↑", transform=ax.transAxes, ha="right", va="top", color=CYAN, fontsize=11,
                bbox={"facecolor": BG, "edgecolor": "#34494f", "pad": 5})
        self.canvas.draw_idle()

    def result_chart(self, document, view):
        self.document = None
        data = document.data
        comparison = data.get("comparison", {})
        ax = self._axes(view.upper())
        if view == "Zbieżność":
            history = data.get("convergence", [])
            ax.plot(history, color=CYAN, linewidth=1.8)
            baseline = comparison.get("baseline", {}).get("totalCost")
            if baseline is not None:
                ax.axhline(baseline, color=AMBER, linestyle="--", linewidth=1, label="Prosta")
                ax.legend(facecolor=PANEL, labelcolor=TEXT)
            ax.set_xlabel("Krok temperatury")
            ax.set_ylabel("Koszt trasy")
        elif view == "Profil wysokości":
            for key, name, color in RUNS:
                path = comparison.get(key, {}).get("path", [])
                if not path:
                    continue
                xyz = np.array([[p["x"], p["y"], p["z"]] for p in path])
                distances = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))]
                ax.plot(distances, xyz[:, 2], color=color, label=name, alpha=.9)
                if key == "sa_ls":
                    xs = np.clip(np.rint(xyz[:, 0]).astype(int), 0, document.width - 1)
                    ys = np.clip(np.rint(xyz[:, 1]).astype(int), 0, document.height - 1)
                    ax.fill_between(distances, document.surface[ys, xs], float(document.ground.min()) - 2, color="#53624b", alpha=.5,
                                    label="Powierzchnia pod trasą SA+LS")
            ax.set_xlabel("Długość trasy 3D [m]")
            ax.set_ylabel("Wysokość [m, układ mapy]")
            ax.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)
        else:
            metric = "totalCost" if view == "Koszt algorytmów" else "threatRisk"
            values = [comparison.get(key, {}).get(metric, 0) for key, _, _ in RUNS]
            bars = ax.bar([name for _, name, _ in RUNS], values, color=[color for _, _, color in RUNS], width=.55)
            for bar, value in zip(bars, values):
                ax.annotate(f"{value:,.2f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                            (0, 6), textcoords="offset points", ha="center", color=TEXT, fontsize=9)
            ax.margins(y=.17)
            ax.set_ylabel("Koszt" if metric == "totalCost" else "Zagrożenie efektywne")
        ax.grid(alpha=.1, color=MUTED)
        self.canvas.draw_idle()


class MissionControl(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UAV // Mission Control")
        self.resize(1520, 960)
        self.setMinimumSize(1100, 720)
        self.document = None
        self.result = None
        self.result_path = None
        self.state = new_state()
        self.undo_stack = []
        self.dirty = False
        self.process = None
        self.worker = None
        self.busy = False
        self.cancelled = False
        self._syncing = False
        self._process_tail = ""
        self._build_ui()
        self.refresh_library()
        self._sync_controls()

    def _build_ui(self):
        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 12)
        header = QtWidgets.QHBoxLayout()
        brand = QtWidgets.QVBoxLayout()
        brand.addWidget(label("UAV // MISSION CONTROL", "brand"))
        brand.addWidget(label("MAPY  /  SCENARIUSZE  /  ANALIZA SYMULACJI", "eyebrow"))
        header.addLayout(brand, 1)
        header.addStretch()
        self.status = label("GOTOWY", "status")
        self.status.setMaximumHeight(36)
        self.status.setMinimumWidth(120)
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        header.addWidget(self.status)
        layout.addLayout(header)
        self.map_info = label("Brak aktywnej mapy · wybierz plik z biblioteki lub wygeneruj obszar", "muted")
        layout.addWidget(self.map_info)
        splitter = QtWidgets.QSplitter()
        library_panel = QtWidgets.QWidget()
        library_layout = QtWidgets.QVBoxLayout(library_panel)
        library_layout.setContentsMargins(0, 0, 10, 0)
        library_layout.addWidget(label("LOKALNA BIBLIOTEKA", "eyebrow"))
        self.library = QtWidgets.QTreeWidget()
        self.library.setHeaderHidden(True)
        self.library.setMinimumWidth(165)
        self.library.itemDoubleClicked.connect(self._library_open)
        library_layout.addWidget(self.library)
        library_layout.addWidget(button("Otwórz plik JSON…", self.open_file))
        library_layout.addWidget(button("Odśwież bibliotekę", self.refresh_library))
        splitter.addWidget(library_panel)
        self.tabs = QtWidgets.QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setSizes([220, 1260])
        layout.addWidget(splitter, 1)
        self._map_tab()
        self._scenario_tab()
        self._result_tab()
        bottom = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        bottom.addWidget(self.progress, 1)
        self.cancel_button = button("Anuluj zadanie", self.cancel_job)
        self.cancel_button.setEnabled(False)
        bottom.addWidget(self.cancel_button)
        layout.addLayout(bottom)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1500)
        self.log.setMaximumHeight(100)
        self.log.setPlaceholderText("Dziennik generowania map i symulacji")
        self.log.setFont(QtGui.QFont("DejaVu Sans Mono", 9))
        layout.addWidget(self.log)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Dane pozostają lokalnie. Pobieranie sieciowe jest używane wyłącznie przy generowaniu map OSM+NMT.")

    def _map_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        controls = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(controls)
        box, box_layout = group("01 / OBSZAR MAPY")
        form = QtWidgets.QFormLayout()
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.latitude = spin(49, 55, 50.2945, 6)
        self.longitude = spin(14, 24.2, 18.6657, 6)
        self.map_width = spin(2, 1000, 200, suffix=" m")
        self.map_height = spin(2, 1000, 200, suffix=" m")
        self.map_name = QtWidgets.QLineEdit("gliwice_centrum")
        for title, item in [("Szerokość geogr.", self.latitude), ("Długość geogr.", self.longitude),
                            ("Szerokość obszaru", self.map_width), ("Wysokość obszaru", self.map_height), ("Nazwa mapy", self.map_name)]:
            form.addRow(title, item)
        box_layout.addLayout(form)
        self.generate_button = button("Generuj OSM + NMT", self.generate_map, True)
        box_layout.addWidget(self.generate_button)
        box_layout.addWidget(label("Środek domyślny: Gliwice. Siatka 1 m, maks. 1 km × 1 km. Dane są zapisywane w pamięci podręcznej.", "muted"))
        form_layout.addWidget(box)
        box, box_layout = group("02 / WARSTWY")
        self.map_layer = QtWidgets.QComboBox()
        self.map_layer.addItems(["Pokrycie terenu", "Wysokość gruntu", "Wysokość powierzchni", "Wysokość przeszkód"])
        self.map_layer.currentTextChanged.connect(self.draw_map)
        box_layout.addWidget(self.map_layer)
        box_layout.addWidget(button("Zapisz widok jako PNG…", lambda: self.export_png(self.map_plot)))
        self.map_details = label("Wybierz mapę, aby zobaczyć jej parametry.", "muted")
        box_layout.addWidget(self.map_details)
        form_layout.addWidget(box)
        form_layout.addStretch()
        form_layout.addWidget(label("Źródła: © OpenStreetMap contributors / ODbL · NMT: GUGiK, Geoportal.gov.pl", "muted"))
        layout.addWidget(scroll_panel(controls))
        self.map_plot = PlotPanel()
        layout.addWidget(self.map_plot, 1)
        self.tabs.addTab(page, "01  MAPA")

    def _scenario_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        controls = QtWidgets.QWidget()
        column = QtWidgets.QVBoxLayout(controls)
        box, content = group("01 / EDYTOR SCENARIUSZA")
        self.scenario_name = QtWidgets.QLineEdit("Nowy scenariusz")
        self.scenario_name.editingFinished.connect(self._settings_changed)
        content.addWidget(self.scenario_name)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["Podgląd / nawigacja", "Dodaj radar", "Ustaw start", "Dodaj checkpoint", "Ustaw koniec", "Usuń najbliższy obiekt"])
        content.addWidget(self.mode)
        content.addWidget(label("Wybierz narzędzie i kliknij mapę. Aby edytować punkty, wyłącz przesuwanie i lupę na pasku mapy.", "muted"))
        form = QtWidgets.QFormLayout()
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.radar_count = spin(0, 100, 3)
        self.radar_range = spin(1, 2000, 40, suffix=" m")
        self.antenna = spin(0, 1000, 15, 1, " m")
        self.radar_strength = spin(0, 1, 1, 2)
        for text, widget in [("Docelowa liczba radarów", self.radar_count), ("Zasięg nowego radaru", self.radar_range),
                             ("Wysokość anteny", self.antenna), ("Siła radaru", self.radar_strength)]:
            form.addRow(text, widget)
        content.addLayout(form)
        self.object_status = label("Radary: 0 / 3 · Checkpointy: 0", "eyebrow")
        self.radar_count.valueChanged.connect(self._update_object_status)
        content.addWidget(self.object_status)
        column.addWidget(box)
        box, content = group("02 / OBIEKTY NA MAPIE")
        self.objects = QtWidgets.QTreeWidget()
        self.objects.setHeaderLabels(["Obiekt", "x / y [m]"])
        self.objects.setMinimumHeight(150)
        self.objects.setMaximumHeight(220)
        content.addWidget(self.objects)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(button("Usuń wybrany", self.delete_selected))
        self.undo_button = button("Cofnij", self.undo)
        row.addWidget(self.undo_button)
        content.addLayout(row)
        column.addWidget(box)
        box, content = group("03 / PARAMETRY LOTU")
        form = QtWidgets.QFormLayout()
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.altitude = spin(.1, 1000, 10, 1, " m")
        self.seed = spin(0, 2147483647, 42)
        self.profile = QtWidgets.QComboBox()
        self.profile.addItems([*PROFILES, "Z pliku"])
        self.profile.setCurrentText("Standard")
        self.profile.currentTextChanged.connect(self._profile_changed)
        self.altitude.valueChanged.connect(self._settings_changed)
        self.seed.valueChanged.connect(self._settings_changed)
        form.addRow("Wysokość nad powierzchnią", self.altitude)
        form.addRow("Seed symulacji", self.seed)
        form.addRow("Profil obliczeń", self.profile)
        content.addLayout(form)
        content.addWidget(label("Obecny model prowadzi lot nad powierzchnią gruntu i przeszkód. Checkpointy są obowiązkowe, w kolejności dodania.", "muted"))
        column.addWidget(box)
        self.save_button = button("Zapisz scenariusz…", self.save_scenario)
        self.run_button = button("URUCHOM SYMULACJĘ", self.run_simulation, True)
        column.addStretch()
        left_panel = QtWidgets.QWidget()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(370)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(scroll_panel(controls), 1)
        left_layout.addWidget(self.save_button)
        left_layout.addWidget(self.run_button)
        layout.addWidget(left_panel)
        self.editor_plot = PlotPanel()
        self.editor_plot.clicked.connect(self.map_click)
        layout.addWidget(self.editor_plot, 1)
        self.tabs.addTab(page, "02  SCENARIUSZ")

    def _result_tab(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        top = QtWidgets.QHBoxLayout()
        self.result_heading = label("BRAK WYNIKÓW — URUCHOM SYMULACJĘ LUB OTWÓRZ ZAPISANY WYNIK", "eyebrow")
        top.addWidget(self.result_heading, 1)
        self.result_view = QtWidgets.QComboBox()
        self.result_view.addItems(["Trasy algorytmów", "Pole radarowe", "Profil wysokości", "Koszt algorytmów", "Zagrożenie algorytmów", "Zbieżność", "Dziennik decyzji"])
        self.result_view.currentTextChanged.connect(self.draw_result)
        top.addWidget(self.result_view)
        self.metrics_toggle = QtWidgets.QPushButton("Tabela metryk")
        self.metrics_toggle.setCheckable(True)
        top.addWidget(self.metrics_toggle)
        self.result_export = button("Eksport PNG…", lambda: self.export_png(self.result_plot))
        self.result_export.setEnabled(False)
        top.addWidget(self.result_export)
        layout.addLayout(top)
        self.result_summary = label("", "muted")
        layout.addWidget(self.result_summary)
        self.metrics = QtWidgets.QTableWidget(4, 7)
        self.metrics.setHorizontalHeaderLabels(["Algorytm", "Koszt", "Długość [m]", "Zagrożenie", "Kolizje", "Punkty", "Status"])
        self.metrics.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.metrics.verticalHeader().setVisible(False)
        self.metrics.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.metrics.setMaximumHeight(168)
        self.metrics.setMinimumHeight(150)
        self.metrics.setVisible(False)
        self.metrics_toggle.toggled.connect(self.metrics.setVisible)
        layout.addWidget(self.metrics)
        self.result_stack = QtWidgets.QStackedWidget()
        self.result_plot = PlotPanel()
        self.result_stack.addWidget(self.result_plot)
        self.decisions = QtWidgets.QPlainTextEdit()
        self.decisions.setReadOnly(True)
        self.decisions.setFont(QtGui.QFont("DejaVu Sans Mono", 10))
        self.result_stack.addWidget(self.decisions)
        layout.addWidget(self.result_stack, 1)
        self.result_note = label("", "muted")
        layout.addWidget(self.result_note)
        self.tabs.addTab(page, "03  WYNIKI")

    def _set_busy(self, busy, message="GOTOWY"):
        self.busy = busy
        self.status.setText(message)
        self.progress.setRange(0, 0 if busy else 1)
        if not busy:
            self.progress.setValue(0)
        self.cancel_button.setEnabled(busy and self.process is not None)
        self.generate_button.setEnabled(not busy)
        self.save_button.setEnabled(not busy and self.document is not None)
        self.run_button.setEnabled(not busy and self.document is not None)
        self.library.setEnabled(not busy)

    def _message(self, message):
        self.log.appendPlainText(message)
        self.statusBar().showMessage(message, 12000)

    def _error(self, message):
        self._message("BŁĄD: " + message)
        QtWidgets.QMessageBox.warning(self, "Nie udało się wykonać zadania", message)

    def _task(self, function, callback, message):
        if self.busy:
            return
        self._set_busy(True, message)
        task = Task(function, self)
        self.worker = task
        task.succeeded.connect(callback)
        task.failed.connect(self._error)
        def finish():
            self.worker = None
            self._set_busy(False)
            task.deleteLater()
        task.finished.connect(finish)
        task.start()

    def refresh_library(self):
        self.library.clear()
        categories = [("MAPY", sorted((ROOT / "data/maps").glob("*.json"))),
                      ("SCENARIUSZE", sorted((ROOT / "data/scenarios").glob("*.json"))),
                      ("WYNIKI", sorted((ROOT / "data/runs").glob("*/result.json"), reverse=True))]
        for title, paths in categories:
            node = QtWidgets.QTreeWidgetItem([f"{title}  /  {len(paths):02d}"])
            node.setForeground(0, QtGui.QColor(GREEN))
            self.library.addTopLevelItem(node)
            for path in paths:
                item = QtWidgets.QTreeWidgetItem([path.parent.name if title == "WYNIKI" else path.stem])
                item.setData(0, QtCore.Qt.UserRole, str(path))
                item.setToolTip(0, str(path))
                node.addChild(item)
            node.setExpanded(True)

    def _library_open(self, item, _column):
        path = item.data(0, QtCore.Qt.UserRole)
        if path:
            self.load_file(path)

    def _confirm_replace(self):
        if not self.dirty:
            return True
        return QtWidgets.QMessageBox.question(self, "Niezapisany scenariusz",
                    "Scenariusz zawiera niezapisane zmiany. Odrzucić je i kontynuować?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes

    def open_file(self):
        if self.busy:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Otwórz mapę, scenariusz lub wynik", str(ROOT / "data"), "JSON (*.json)")
        if path:
            self.load_file(path)

    def load_file(self, path, confirm=True):
        if self.busy or (confirm and not self._confirm_replace()):
            return
        self._task(lambda: MapDocument.load(path), self._loaded, "WCZYTYWANIE PLIKU")

    def _loaded(self, document):
        self.document = document
        self.state = state_from_document(document.data)
        # Incomplete scenarios are valid drafts; loaded objects are checked too.
        try:
            validate_state(self.state, document.width, document.height, require_mission=False)
        except ValueError as error:
            self._message(f"Scenariusz wymaga poprawy przed uruchomieniem: {error}")
        self.undo_stack.clear()
        self.dirty = False
        self._sync_controls()
        source = "OSM + NMT" if document.data.get("metadata") else "PROCEDURALNA"
        name = document.path.name if document.path else "mapa"
        self.map_info.setText(f"{name}  ·  {document.width} × {document.height} m  ·  {source}  ·  siatka 1 m")
        metadata = document.data.get("metadata", {})
        center = metadata.get("centerLatLon")
        if center:
            self.latitude.setValue(center[0])
            self.longitude.setValue(center[1])
        self.map_width.setValue(min(1000, document.width))
        self.map_height.setValue(min(1000, document.height))
        self.map_details.setText(f"Rozmiar: {document.width} × {document.height} m\n"
                                 f"Grunt: {document.ground.min():.1f}–{document.ground.max():.1f} m\n"
                                 f"Budynki / części: {len(metadata.get('buildings', []))}\n"
                                 f"Nieznane pokrycie: {metadata.get('unknownLandCoverCells', 'brak informacji')} komórek\n"
                                 "Wysokości budynków mogą być szacowane; szczegóły znajdują się w metadanych mapy.")
        self.draw_map()
        self._draw_editor()
        if document.data.get("comparison"):
            self._show_result(document)
        else:
            self.tabs.setCurrentIndex(1 if document.data.get("scenario") else 0)
        self._message(f"Wczytano: {document.path}")

    def _sync_controls(self):
        self._syncing = True
        self.scenario_name.setText(str(self.state["name"]))
        self.seed.setValue(self.state["seed"])
        self.altitude.setValue(self.state["flightAltitude"])
        self.profile.setCurrentText("Z pliku")
        self.radar_count.setValue(max(3, len(self.state["radars"])))
        self._syncing = False
        self._refresh_objects()
        self._set_busy(self.busy, self.status.text())

    def _snapshot(self):
        self.undo_stack.append(copy.deepcopy(self.state))
        self.undo_stack = self.undo_stack[-100:]

    def _changed(self):
        self.dirty = True
        self._refresh_objects()
        self._draw_editor()
        if self.result:
            self.result_note.setText("Scenariusz został zmieniony. Wyświetlane wyniki dotyczą wcześniejszego, zapisanego uruchomienia.")

    def _settings_changed(self, *_args):
        if self._syncing or self.busy:
            return
        changes = {"name": self.scenario_name.text().strip() or "Scenariusz", "seed": self.seed.value(), "flightAltitude": self.altitude.value()}
        if any(self.state[key] != value for key, value in changes.items()):
            self._snapshot()
            self.state.update(changes)
            self._changed()

    def _profile_changed(self, name):
        if self._syncing or name == "Z pliku" or self.busy:
            return
        self._snapshot()
        self.state["optimizer"] = optimizer_profile(name, max(self.document.width, self.document.height) if self.document else 200)
        self._changed()

    def _update_object_status(self):
        self.object_status.setText(f"Radary: {len(self.state['radars'])} / {self.radar_count.value()}  ·  Checkpointy: {len(self.state['checkpoints'])}")

    def _refresh_objects(self):
        self.objects.clear()
        entries = [(f"R{r['id']} · {r['range']:g} m", "radar", i, r) for i, r in enumerate(self.state["radars"])]
        entries += [("START", "start", 0, self.state["start"])]
        entries += [(f"C{i + 1} · checkpoint", "checkpoint", i, p) for i, p in enumerate(self.state["checkpoints"])]
        entries += [("KONIEC", "end", 0, self.state["end"])]
        for name, kind, index, point in entries:
            if point is None:
                continue
            item = QtWidgets.QTreeWidgetItem([name, f"{point['x']:g} / {point['y']:g}"])
            item.setData(0, QtCore.Qt.UserRole, (kind, index))
            self.objects.addTopLevelItem(item)
        self.objects.resizeColumnToContents(0)
        self.undo_button.setEnabled(bool(self.undo_stack) and not self.busy)
        self._update_object_status()

    def _draw_editor(self):
        if self.document:
            self.editor_plot.map(self.document, state=self.state, title="EDYTOR / " + self.state["name"].upper())

    def draw_map(self, *_args):
        if self.document:
            layer = self.map_layer.currentText()
            if layer in {"Wysokość gruntu", "Wysokość przeszkód"} and not self.document.has_ground:
                self.map_plot.empty("BRAK ODDZIELNEJ WARSTWY GRUNTU", "Ta mapa proceduralna zapisuje tylko wysokość powierzchni.")
            else:
                self.map_plot.map(self.document, layer)

    def map_click(self, x, y):
        if self.busy or self.document is None:
            return
        mode = self.mode.currentIndex()
        if mode == 0:
            cell = self.document.data["cells"][y][x]
            self.statusBar().showMessage(f"x={x}, y={y} · {cell['terrain']} · powierzchnia {cell['elevation']:.1f} m", 8000)
            return
        if mode == 5:
            candidates = [("radar", i, p) for i, p in enumerate(self.state["radars"])]
            candidates += [("checkpoint", i, p) for i, p in enumerate(self.state["checkpoints"])]
            candidates += [(key, 0, self.state[key]) for key in ("start", "end") if self.state[key]]
            if candidates:
                kind, index, point = min(candidates, key=lambda entry: (entry[2]["x"] - x) ** 2 + (entry[2]["y"] - y) ** 2)
                if np.hypot(point["x"] - x, point["y"] - y) <= max(5, max(self.document.width, self.document.height) * .02):
                    self._delete(kind, index)
            return
        if mode == 1 and len(self.state["radars"]) >= self.radar_count.value():
            self._message("Osiągnięto docelową liczbę radarów. Zwiększ limit lub usuń radar.")
            return
        if mode == 3 and len(self.state["checkpoints"]) >= 98:
            self._message("Osiągnięto limit 98 checkpointów.")
            return
        self._snapshot()
        if mode == 1:
            radar_id = max((r["id"] for r in self.state["radars"]), default=0) + 1
            self.state["radars"].append({"id": radar_id, "x": x, "y": y, "range": self.radar_range.value(),
                                         "antennaHeight": self.antenna.value(), "baseThreat": self.radar_strength.value()})
        else:
            point = {"x": x, "y": y}
            if mode == 2:
                point["name"] = "Start"
                self.state["start"] = point
            elif mode == 3:
                point["name"] = f"Checkpoint {len(self.state['checkpoints']) + 1}"
                self.state["checkpoints"].append(point)
            elif mode == 4:
                point["name"] = "Koniec"
                self.state["end"] = point
        self._changed()

    def _delete(self, kind, index):
        if self.busy:
            return
        self._snapshot()
        if kind in {"start", "end"}:
            self.state[kind] = None
        else:
            del self.state["radars" if kind == "radar" else "checkpoints"][index]
        self._changed()

    def delete_selected(self):
        item = self.objects.currentItem()
        if item:
            self._delete(*item.data(0, QtCore.Qt.UserRole))

    def undo(self):
        if self.undo_stack and not self.busy:
            self.state = self.undo_stack.pop()
            self._sync_controls()
            self._changed()

    def save_scenario(self):
        if self.busy or self.document is None:
            return
        self._settings_changed()
        try:
            document = scenario_document(self.document, self.state, require_mission=False)
        except ValueError as error:
            self._error(str(error))
            return
        name = self._slug(self.state["name"])
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz kompletny scenariusz", str(ROOT / "data/scenarios" / (name + ".json")), "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        def saved(saved_path):
            self.dirty = False
            self._message(f"Zapisano samodzielny scenariusz: {saved_path}")
            self.refresh_library()
        self._task(lambda: write_document(path, document), saved, "ZAPISYWANIE SCENARIUSZA")

    @staticmethod
    def _slug(name):
        return re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")[:70] or "scenariusz"

    def generate_map(self):
        if self.busy or not self._confirm_replace():
            return
        name = self._slug(self.map_name.text())
        output = ROOT / "data/maps" / (name + ".json")
        if output.exists():
            output = output.with_name(f"{name}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:4]}.json")
        args = [str(ROOT / "python/main.py"), "import-map", "--center", str(self.latitude.value()), str(self.longitude.value()),
                "--size", str(self.map_width.value()), str(self.map_height.value()), "--output", str(output)]
        def generated():
            self.refresh_library()
            self.load_file(output, confirm=False)
        self._start_process(sys.executable, args, generated, "POBIERANIE OSM + NMT")

    def run_simulation(self):
        if self.busy or self.document is None:
            return
        self._settings_changed()
        try:
            document = scenario_document(self.document, self.state)
        except ValueError as error:
            self._error(str(error))
            return
        executable = ROOT / "build/UAVPlanner"
        if not executable.is_file():
            self._error("Brak build/UAVPlanner. Wykonaj: cmake -S . -B build && cmake --build build -j 4")
            return
        folder = ROOT / "data/runs" / f"{datetime.now():%Y%m%d_%H%M%S}_{self._slug(self.state['name'])}_{uuid.uuid4().hex[:4]}"
        snapshot, output = folder / "scenario.json", folder / "result.json"
        def prepared(_path):
            # Start after the file-writing QThread has fully finished.
            self._pending_run = (executable, snapshot, output)
        def launch():
            pending = getattr(self, "_pending_run", None)
            if pending:
                self._pending_run = None
                exe, input_path, output_path = pending
                def completed():
                    self.refresh_library()
                    self._task(lambda: MapDocument.load(output_path), self._show_result, "WCZYTYWANIE WYNIKÓW")
                self._start_process(str(exe), ["--scenario", str(input_path), "--output", str(output_path)], completed, "SYMULACJA W TOKU")
        self._task(lambda: write_document(snapshot, document), prepared, "ZAPIS MIGAWKI SCENARIUSZA")
        if self.worker:
            self.worker.finished.connect(launch)

    def _start_process(self, program, args, callback, message):
        if self.busy:
            return
        process = QtCore.QProcess(self)
        self.process = process
        self.cancelled = False
        self._process_tail = ""
        self._output_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        process.setWorkingDirectory(str(ROOT))
        process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        environment = QtCore.QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(self._read_output)
        def finished(code, exit_status):
            if self.process is not process:
                return
            self._read_output()
            self.process = None
            self._set_busy(False)
            process.deleteLater()
            if self.cancelled:
                self._message("Zadanie anulowane. Poprzednie mapy i wyniki pozostają zapisane.")
            elif code == 0 and exit_status == QtCore.QProcess.NormalExit:
                callback()
            else:
                self._error("Proces zakończył się błędem.\n" + self._process_tail[-2500:])
        process.finished.connect(finished)
        def failed(error):
            if error == QtCore.QProcess.FailedToStart and self.process is process:
                self.process = None
                self._set_busy(False)
                self._error("Nie można uruchomić procesu: " + process.errorString())
                process.deleteLater()
        process.errorOccurred.connect(failed)
        self._set_busy(True, message)
        self._message(message)
        process.start(program, args)

    def _read_output(self):
        if self.process:
            text = self._output_decoder.decode(bytes(self.process.readAllStandardOutput()))
            if text:
                self._process_tail = (self._process_tail + text)[-10000:]
                cursor = self.log.textCursor()
                cursor.movePosition(QtGui.QTextCursor.End)
                cursor.insertText(text)
                self.log.setTextCursor(cursor)

    def cancel_job(self):
        if self.process:
            self.cancelled = True
            process = self.process
            process.terminate()
            QtCore.QTimer.singleShot(2000, lambda: process.kill() if self.process is process and process.state() != QtCore.QProcess.NotRunning else None)

    def _show_result(self, document):
        self.result = document
        self.result_path = document.path
        data = document.data
        self.result_heading.setText("WYNIK / " + str(data.get("scenario", {}).get("name", document.path.stem if document.path else "symulacja")).upper())
        for row, (key, name, color) in enumerate(RUNS):
            run = data.get("comparison", {}).get(key, {})
            values = [name, f"{run.get('totalCost', 0):,.2f}", f"{run.get('distance', 0):,.1f}",
                      f"{run.get('threatRisk', 0):,.2f}", str(run.get("collisionCount", 0)), str(run.get("waypointsCount", 0)),
                      "WYKONALNA" if run.get("isFeasible") else "KOLIZJE"]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setForeground(QtGui.QColor(color))
                if col == 6:
                    item.setForeground(QtGui.QColor(GREEN if run.get("isFeasible") else RED))
                self.metrics.setItem(row, col, item)
        config = data.get("scenario", {})
        best = data.get("comparison", {}).get("sa_ls", {})
        self.result_summary.setText(f"SA + LS  /  koszt {best.get('totalCost', 0):,.2f}  ·  "
                                    f"dystans {best.get('distance', 0):,.1f} m  ·  "
                                    f"zagrożenie {best.get('threatRisk', 0):,.2f}  ·  "
                                    f"kolizje {best.get('collisionCount', 0)}  ·  "
                                    + ("WYKONALNA" if best.get("isFeasible") else "KOLIZJE"))
        self.result_note.setText(f"Seed: {config.get('seed', 'brak w pliku')} · Źródło: {document.path}\n"
                                 "Każde uruchomienie zachowuje pełną migawkę scenariusza. Wynik można otworzyć ponownie z biblioteki.")
        self.decisions.setPlainText("\n\n".join(f"[{event.get('phase', '')} / {event.get('iteration', 0)}] {event.get('action', '')}\n"
                                    f"{event.get('details', '')}\nKoszt: {event.get('costBefore', 0):.3f} → {event.get('costAfter', 0):.3f}"
                                    for event in data.get("decisionLog", [])) or "Brak dziennika decyzji w tym pliku.")
        self.draw_result()
        self.tabs.setCurrentIndex(2)
        self._message(f"Gotowe wyniki: {document.path}")

    def draw_result(self, *_args):
        if self.result is None:
            return
        view = self.result_view.currentText()
        self.result_export.setEnabled(view != "Dziennik decyzji")
        self.result_stack.setCurrentIndex(1 if view == "Dziennik decyzji" else 0)
        if view in {"Trasy algorytmów", "Pole radarowe"}:
            state = state_from_document(self.result.data)
            self.result_plot.map(self.result, view, state, self.result.data.get("comparison"), title=view.upper())
        elif view != "Dziennik decyzji":
            self.result_plot.result_chart(self.result, view)

    def export_png(self, panel):
        if self.document is None and self.result is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Eksport widoku", str(ROOT / "data" / "widok.png"), "PNG (*.png)")
        if path:
            try:
                panel.figure.savefig(path if path.lower().endswith(".png") else path + ".png", dpi=170, facecolor=BG)
                self._message("Zapisano widok: " + path)
            except OSError as error:
                self._error(str(error))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage("Poczekaj na zakończenie odczytu lub zapisu pliku.")
            event.ignore()
            return
        if not self._confirm_replace():
            event.ignore()
            return
        if self.process:
            process = self.process
            self.cancelled = True
            process.terminate()
            if not process.waitForFinished(2000):
                process.kill()
                process.waitForFinished(2000)
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, help="Mapa, scenariusz lub wynik do otwarcia")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName("UAV Mission Control")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MissionControl()
    window.show()
    if args.map:
        window.load_file(args.map)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
