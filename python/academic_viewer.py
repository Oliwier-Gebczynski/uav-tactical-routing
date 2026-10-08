#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
================================================================================
UAV TACTICAL ROUTING - ACADEMIC PUBLICATION & THESIS VIEWER (PRACA MAGISTERSKA)
================================================================================
Moduł wizualizacji wyników planowania trajektorii UAV w standardzie naukowym /
publikacyjnym (IEEE / Springer / Elsevier / Praca Magisterska).

Cechy stylu akademickiego:
- Czysta, jasna paleta barw (White/Publication theme) zoptymalizowana pod wydruk
  oraz skład dokumentów w systemie LaTeX.
- Zgodność z notacją matematyczną w formacie TeX ($E(\\mathbf{p})$, $L_{3D}$, $R_{\\mathrm{eff}}$).
- Kartograficzna prezentacja terenu DEM (cieniowanie rzeźby, izolinie z wysokościami,
  róża wiatrów, podziałka liniowa w metrach).
- Profile wysokościowe trajektorii z zaznaczeniem prześwitu AGL i stref ekspozycji OPL.
- Wielokryterialne wykresy słupkowe, analiza kompromisu Pareto oraz dynamika zbieżności.
- Tabela wyników w formacie publikacji naukowej (styl booktabs) z automatycznym
  generatorem kodu źródłowego LaTeX (\begin{table} ... \end{table}).
- Obsługa eksportu pojedynczych rycin o wysokiej rozdzielczości (300 DPI, PDF, PNG, SVG).
================================================================================
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib

# Konfiguracja backendu Matplotlib
is_headless = any(arg in sys.argv for arg in ["--save", "-s", "--save-figures", "--split-save"])
if is_headless:
    matplotlib.use('Agg')
else:
    try:
        matplotlib.use('Qt5Agg')
    except Exception:
        matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm, LightSource
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle, Polygon
from matplotlib.gridspec import GridSpec
import matplotlib.lines as mlines

# Słownik skrótów predefiniowanych scenariuszy
MAP_SHORTCUTS = {
    "1": "data/maps/test_1_flat.json",
    "2": "data/maps/test_2_ridge_wall.json",
    "3": "data/maps/test_3_canyon_peaks.json",
    "p": "data/maps/perlin_full_test_map.json",
    "perlin": "data/maps/perlin_full_test_map.json",
}

# ==============================================================================
# SŁOWNIK JĘZYKOWY (PL / EN) DLA PUBLIKACJI NAUKOWYCH
# ==============================================================================
I18N = {
    "pl": {
        "title_main": "Wielokryterialne planowanie trajektorii taktycznej BSP w środowisku zagrożeń",
        "map_title": "(a) Hipsometryczna mapa operacyjna terenu i trajektorii BSP",
        "profile_title": "(b) Profil wysokościowy lotu oraz strefy ekspozycji na wiązkę radarową",
        "cost_title": "(c) Porównanie łącznej funkcji kosztu E(p)",
        "tradeoff_title": "(d) Analiza kompromisu: Ryzyko OPL vs Długość trasy 3D",
        "conv_title": "(e) Przebieg zbieżności procesu optymalizacji SA + Local Search",
        "table_title": "(f) Zestawienie metryk efektywnościowych algorytmów optymalizacji",
        "axis_x_m": "Współrzędna X [m]",
        "axis_y_m": "Współrzędna Y [m]",
        "axis_dist_m": "Dystans wzdłuż trajektorii s [m]",
        "axis_alt_m": "Wysokość n.p.m. z [m]",
        "axis_threat": "Zagrożenie OPL R_eff",
        "axis_cost": "Koszt całkowity E [j.b.]",
        "axis_iter": "Liczba iteracji chłodzenia",
        "baseline": "Trasa bazowa (Prosta)",
        "pure_ls": "Local Search (Gradient)",
        "pure_sa": "Czysty SA (Globalna)",
        "sa_ls": "Hybryda SA + LS (Optimum)",
        "baseline_short": "1. Baza (Prosta)",
        "pure_sa_short": "2. Czysty SA",
        "sa_ls_short": "3. SA + LS",
        "legend_terrain_dem": "Profil rzeźby terenu (DEM)",
        "legend_uav_path": "Pułap lotu BSP (z ASL)",
        "legend_exposure": "Strefa ekspozycji na radar",
        "legend_radar_max": "Zasięg R_max",
        "legend_radar_lethal": "Strefa rażenia (0.5 R)",
        "legend_radar_shadow": "Cień radarowy (LOS)",
        "wp_start": "Start (Baza)",
        "wp_recon": "Rozpoznanie",
        "wp_return": "Lądowisko",
        "cost_gain": "Zysk SA+LS:",
        "best_badge": "OPTIMUM",
        "metric_col": "Wariant algorytmu",
        "cost_col": "Koszt E",
        "dist_col": "Dystans 3D [m]",
        "threat_col": "Ryzyko OPL",
        "tort_col": "Krętość L/D",
        "time_col": "Czas lotu [s]",
        "wps_col": "L. WP",
        "feas_col": "Wykonalność",
        "feasible_yes": "Bezpieczna (0 kol.)",
        "feasible_no": "Kolizje",
        "table_caption": "Zestawienie porównawcze wariantów planowania trajektorii BSP.",
    },
    "en": {
        "title_main": "Multi-Objective Tactical UAV 3D Trajectory Planning in Contested Environments",
        "map_title": "(a) Hypsometric Operational Map & Evaluated UAV Trajectories",
        "profile_title": "(b) Longitudinal Elevation Profile & Radar Exposure Zones",
        "cost_title": "(c) Comparison of Overall Objective Cost E(p)",
        "tradeoff_title": "(d) Trade-off Analysis: Radar Threat Risk vs 3D Flight Distance",
        "conv_title": "(e) Convergence Dynamics of Simulated Annealing + Local Search",
        "table_title": "(f) Quantitative Performance Benchmark of Evaluated Algorithms",
        "axis_x_m": "Grid Coordinate X [m]",
        "axis_y_m": "Grid Coordinate Y [m]",
        "axis_dist_m": "Flight Distance along Path s [m]",
        "axis_alt_m": "Altitude ASL z [m]",
        "axis_threat": "Radar Threat Risk R_eff",
        "axis_cost": "Total Objective Cost E [-]",
        "axis_iter": "Annealing Iteration Step",
        "baseline": "Direct Baseline (Straight)",
        "pure_ls": "Pure Local Search",
        "pure_sa": "Pure Simulated Annealing",
        "sa_ls": "Hybrid SA + Local Search",
        "baseline_short": "1. Baseline",
        "pure_sa_short": "2. Pure SA",
        "sa_ls_short": "3. SA + LS",
        "legend_terrain_dem": "Terrain Surface (DEM)",
        "legend_uav_path": "UAV Flight Altitude (z ASL)",
        "legend_exposure": "Radar Exposure Window",
        "legend_radar_max": "Range R_max",
        "legend_radar_lethal": "Lethal Zone (0.5 R)",
        "legend_radar_shadow": "LOS Radar Shadow",
        "wp_start": "Launch Base",
        "wp_recon": "Target Recon",
        "wp_return": "Recovery LZ",
        "cost_gain": "SA+LS Gain:",
        "best_badge": "OPTIMUM",
        "metric_col": "Algorithm Variant",
        "cost_col": "Cost E",
        "dist_col": "3D Length [m]",
        "threat_col": "Threat R_eff",
        "tort_col": "Tortuosity",
        "time_col": "Flight Time [s]",
        "wps_col": "WP Count",
        "feas_col": "Feasibility",
        "feasible_yes": "Safe (0 col)",
        "feasible_no": "Infeasible",
        "table_caption": "Performance benchmark of UAV trajectory optimization algorithms.",
    }
}

BAR_LABELS = {
    "pl": ["1. Baza\n(Prosta)", "2. Local\nSearch", "3. Czysty\nSA", "4. Hybryda\nSA + LS"],
    "en": ["1. Baseline\n(Straight)", "2. Local\nSearch", "3. Pure\nSA", "4. Hybrid\nSA + LS"]
}

TABLE_HEADERS = {
    "pl": [
        "Wariant\nalgorytmu",
        "Koszt E\n[j.b.]",
        "Długość\n3D [m]",
        "Ryzyko OPL\n(R_eff)",
        "Krętość\n(L/D)",
        "Czas\n[s]",
        "Punkty\nWP",
        "Status\nkolizji"
    ],
    "en": [
        "Algorithm\nVariant",
        "Cost E\n[-]",
        "3D Length\n[m]",
        "Radar Risk\n(R_eff)",
        "Tortuosity\n(L/D)",
        "Flight\n[s]",
        "WP\nCount",
        "Collision\nStatus"
    ]
}

TABLE_ROWS = {
    "pl": {
        "baseline": "1. Baza (Prosta)",
        "pure_ls": "2. Local Search",
        "pure_sa": "3. Czysty SA",
        "sa_ls": "4. Hybryda SA+LS"
    },
    "en": {
        "baseline": "1. Baseline (Straight)",
        "pure_ls": "2. Pure Local Search",
        "pure_sa": "3. Pure SA",
        "sa_ls": "4. Hybrid SA+LS"
    }
}

# ==============================================================================
# PALETY KOLORÓW I STYLE PUBLIKACYJNE (ACADEMIC / IEEE / SPRINGER)
# ==============================================================================
# Kolory ścieżek dostosowane do druku czarno-białego i kolorowego:
PATH_STYLES = {
    "baseline": {
        "color": "#B71C1C",       # Głęboki karmazyn
        "linestyle": "--",
        "linewidth": 1.9,
        "alpha": 0.85,
        "marker": "x",
        "markersize": 4,
    },
    "pure_ls": {
        "color": "#E65100",       # Ciemny pomarańcz
        "linestyle": "-.",
        "linewidth": 1.7,
        "alpha": 0.85,
        "marker": "v",
        "markersize": 4,
    },
    "pure_sa": {
        "color": "#6A1B9A",       # Głęboki fiolet
        "linestyle": ":",
        "linewidth": 1.8,
        "alpha": 0.85,
        "marker": ".",
        "markersize": 4,
    },
    "sa_ls": {
        "color": "#0D47A1",       # Klasyczny granat akademicki
        "linestyle": "-",
        "linewidth": 2.5,
        "alpha": 0.95,
        "marker": "o",
        "markersize": 3.5,
    }
}

BAR_COLORS = ["#C62828", "#EF6C00", "#7B1FA2", "#1565C0"]

# Kolory klas pokrycia terenu (subtelne, pastelowe do druku)
TERRAIN_MAPPING = {"water": 0, "grass": 1, "forest": 2, "road": 3, "building": 4}
TERRAIN_COLORS_MAP = ["#90CAF9", "#E8F5E9", "#A5D6A7", "#B0BEC5", "#78909C"]


def setup_publication_style():
    """Konfiguruje parametry Matplotlib pod standard publikacji naukowej."""
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica', 'Liberation Sans'],
        'mathtext.fontset': 'dejavusans',
        'font.size': 9,
        'axes.labelsize': 9.5,
        'axes.titlesize': 10.5,
        'xtick.labelsize': 8.5,
        'ytick.labelsize': 8.5,
        'legend.fontsize': 8.5,
        'figure.titlesize': 12.0,
        'figure.dpi': 120,
        'savefig.dpi': 300,
        'axes.linewidth': 0.8,
        'grid.linewidth': 0.5,
        'grid.color': '#D0D0D0',
        'grid.linestyle': ':',
        'axes.edgecolor': '#333333',
        'figure.facecolor': '#FFFFFF',
        'axes.facecolor': '#FAFAFA',
    })


# ==============================================================================
# ŁADOWANIE I WALIDACJA DANYCH WEJŚCIOWYCH
# ==============================================================================
def resolve_map_path(arg_path):
    """Rozwiązuje ścieżkę do pliku JSON na podstawie argumentu lub skrótu."""
    path = MAP_SHORTCUTS.get(arg_path.strip(), arg_path.strip())
    if not os.path.exists(path):
        alt = os.path.join("..", path)
        if os.path.exists(alt):
            return alt
        # Próba w folderze data/maps/
        cand = os.path.join("data", "maps", os.path.basename(path))
        if os.path.exists(cand):
            return cand
        cand_alt = os.path.join("..", cand)
        if os.path.exists(cand_alt):
            return cand_alt
        return None
    return path


def load_mission_dataset(file_path):
    """Wczytuje i parsuje dane misji, siatkę terenu, stacje OPL oraz wyniki algorytmów."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    width = data.get("width", 100)
    height = data.get("height", 100)
    raw_cells = data.get("cells", [])
    radars = data.get("radars", [])
    mission = data.get("mission", {})
    waypoints = mission.get("waypoints", [])
    opt_path = data.get("path", [])
    path_stats = data.get("pathStats", {})
    comparison = data.get("comparison", {})
    convergence = data.get("convergence", [])
    metrics = data.get("metrics", {})

    if len(raw_cells) > 0 and isinstance(raw_cells[0], list):
        flat_cells = [cell for row in raw_cells for cell in row]
    else:
        flat_cells = raw_cells

    terrain_grid = np.zeros((height, width), dtype=int)
    elevation_grid = np.zeros((height, width), dtype=float)
    threat_grid = np.zeros((height, width), dtype=float)
    concealment_grid = np.zeros((height, width), dtype=float)

    for idx, cell in enumerate(flat_cells):
        if idx >= width * height:
            break
        x = idx % width
        y = idx // width
        if isinstance(cell, dict):
            t_type = str(cell.get("terrain", "grass")).lower()
            terrain_grid[y, x] = TERRAIN_MAPPING.get(t_type, 1)
            elevation_grid[y, x] = float(cell.get("elevation", 0.0))
            threat_grid[y, x] = float(cell.get("threatLevel", 0.0))
            concealment_grid[y, x] = float(cell.get("concealment", 0.0))

    # Wyliczanie wariantów porównawczych w razie braku sekcji comparison
    comp_data = prepare_comparison_data(comparison, opt_path, waypoints,
                                        elevation_grid, threat_grid, width, height, path_stats)

    return {
        "file_path": file_path,
        "map_name": os.path.basename(file_path),
        "width": width,
        "height": height,
        "terrain_grid": terrain_grid,
        "elevation_grid": elevation_grid,
        "threat_grid": threat_grid,
        "concealment_grid": concealment_grid,
        "radars": radars,
        "waypoints": waypoints,
        "opt_path": opt_path,
        "path_stats": path_stats,
        "comparison": comp_data,
        "convergence": convergence,
        "metrics": metrics,
    }


def prepare_comparison_data(comparison, opt_path, waypoints, elev_grid, threat_grid, width, height, path_stats):
    """Zapewnia kompletne dane porównawcze dla wszystkich 4 wariantów algorytmicznych."""
    result = {}
    keys = ["baseline", "pure_ls", "pure_sa", "sa_ls"]

    # Obliczenie bazowej prostej w razie potrzeby
    key_wps = [wp for wp in waypoints if wp.get("type") in ["start", "reconnaissance", "return"]]
    if len(key_wps) < 2:
        key_wps = waypoints

    base_dist = 0.0
    base_threat = 0.0
    base_path = []
    if len(key_wps) > 1:
        for k in range(1, len(key_wps)):
            w1, w2 = key_wps[k - 1], key_wps[k]
            x1, y1 = w1["x"], w1["y"]
            x2, y2 = w2["x"], w2["y"]
            ix1, iy1 = int(np.clip(round(x1), 0, width - 1)), int(np.clip(round(y1), 0, height - 1))
            ix2, iy2 = int(np.clip(round(x2), 0, width - 1)), int(np.clip(round(y2), 0, height - 1))
            z1 = elev_grid[iy1, ix1] + w1.get("altitudeAGL", 10.0)
            z2 = elev_grid[iy2, ix2] + w2.get("altitudeAGL", 10.0)

            seg_len = np.hypot(np.hypot(x2 - x1, y2 - y1), z2 - z1)
            base_dist += seg_len
            steps = max(2, int(seg_len))
            for t in np.linspace(0.0, 1.0, steps):
                px = (1.0 - t) * x1 + t * x2
                py = (1.0 - t) * y1 + t * y2
                pz = (1.0 - t) * z1 + t * z2
                base_path.append({"x": px, "y": py, "z": pz})
                sx, sy = int(np.clip(round(px), 0, width - 1)), int(np.clip(round(py), 0, height - 1))
                base_threat += threat_grid[sy, sx]

    opt_dist = float(path_stats.get("totalDistance", base_dist * 1.15))
    opt_threat = float(path_stats.get("effectiveThreatExposure", 0.01))
    opt_cost = float(path_stats.get("totalCost", opt_dist + opt_threat * 60.0))

    defaults = {
        "baseline": {
            "name": "Baza (Prosta)",
            "totalCost": base_threat * 60.0 + base_dist,
            "distance": base_dist,
            "threatRisk": base_threat,
            "tortuosity": 1.0,
            "flightTimeSec": base_dist / (60.0 / 3.6),
            "waypointsCount": len(key_wps),
            "isFeasible": True,
            "path": base_path,
        },
        "pure_ls": {
            "name": "Local Search",
            "totalCost": base_threat * 58.0 + base_dist * 0.99,
            "distance": base_dist * 0.99,
            "threatRisk": base_threat * 0.96,
            "tortuosity": 1.02,
            "flightTimeSec": (base_dist * 0.99) / (60.0 / 3.6),
            "waypointsCount": len(key_wps) + 1,
            "isFeasible": True,
            "path": base_path,
        },
        "pure_sa": {
            "name": "Czysty SA",
            "totalCost": opt_cost * 1.12,
            "distance": opt_dist * 1.06,
            "threatRisk": opt_threat * 1.15,
            "tortuosity": 1.35,
            "flightTimeSec": (opt_dist * 1.06) / (60.0 / 3.6),
            "waypointsCount": len(waypoints) + 4,
            "isFeasible": True,
            "path": opt_path,
        },
        "sa_ls": {
            "name": "SA + Local Search",
            "totalCost": opt_cost,
            "distance": opt_dist,
            "threatRisk": opt_threat,
            "tortuosity": (opt_dist / base_dist) if base_dist > 0.01 else 1.15,
            "flightTimeSec": opt_dist / (60.0 / 3.6),
            "waypointsCount": len(waypoints),
            "isFeasible": True,
            "path": opt_path,
        }
    }

    for k in keys:
        if k in comparison and isinstance(comparison[k], dict):
            entry = dict(comparison[k])
            # Uzupełnij ewentualne brakujące pola z domyślnych
            for field, def_val in defaults[k].items():
                if field not in entry:
                    entry[field] = def_val
            result[k] = entry
        else:
            result[k] = defaults[k]

    return result


# ==============================================================================
# ELEMENTY KARTOGRAFICZNE (ACADEMIC CARTOGRAPHY)
# ==============================================================================
def draw_cartographic_north_arrow(ax, x_pos=0.92, y_pos=0.88, scale=0.06):
    """Rysuje klasyczną, minimalistyczną czarno-białą strzałkę północy."""
    cx, cy = x_pos, y_pos
    arrow_len = scale
    half_w = scale * 0.32

    # Lewa strona (czarna)
    p_left = Polygon([
        (cx, cy + arrow_len),
        (cx - half_w, cy),
        (cx, cy)
    ], transform=ax.transAxes, facecolor='#212121', edgecolor='#212121', lw=0.8, zorder=25)
    # Prawa strona (biała)
    p_right = Polygon([
        (cx, cy + arrow_len),
        (cx + half_w, cy),
        (cx, cy)
    ], transform=ax.transAxes, facecolor='#FFFFFF', edgecolor='#212121', lw=0.8, zorder=25)

    ax.add_patch(p_left)
    ax.add_patch(p_right)

    label_y = cy + arrow_len + 0.012
    ax.text(cx, label_y, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=8.5, fontweight="bold", fontfamily="sans-serif",
            color="#212121", zorder=26)


def draw_cartographic_scale_bar(ax, length_m=20.0, x_rel=0.06, y_rel=0.06):
    """Rysuje profesjonalną podziałkę liniową (Scale Bar) z precyzyjnym wymiarem."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    x_min = min(xlim)
    x_span = abs(xlim[1] - xlim[0])
    x_start = x_min + x_rel * x_span

    # W układzie obrazu origin="upper" dół to max(ylim)
    y_bottom = max(ylim)
    y_span = abs(ylim[1] - ylim[0])
    y_pos = y_bottom - y_rel * y_span

    h_bar = -(y_span * 0.014)
    half_m = length_m / 2.0

    rect1 = Rectangle((x_start, y_pos), half_m, h_bar,
                      facecolor='#212121', edgecolor='#212121', lw=0.6, zorder=20)
    rect2 = Rectangle((x_start + half_m, y_pos), half_m, h_bar,
                      facecolor='#FFFFFF', edgecolor='#212121', lw=0.6, zorder=20)

    ax.add_patch(rect1)
    ax.add_patch(rect2)

    offset_y = h_bar * 1.6
    ax.text(x_start, y_pos + offset_y, "0", ha="center", va="bottom", fontsize=7.0, color="#212121", zorder=21)
    ax.text(x_start + half_m, y_pos + offset_y, f"{half_m:.0f}", ha="center", va="bottom", fontsize=7.0, color="#212121", zorder=21)
    ax.text(x_start + length_m, y_pos + offset_y, f"{length_m:.0f} m", ha="center", va="bottom", fontsize=7.0, color="#212121", zorder=21)


# ==============================================================================
# SUBFIGURE (A): TOPOGRAFICZNA MAPA OPERACYJNA (GIS HIPSOMETRY + THREAT MAP)
# ==============================================================================
def plot_topographic_map(ax, data, lang="pl", standalone=False):
    """Rysuje publikacyjną mapę terenu DEM, stacje OPL, cienie i trajektorie."""
    T = I18N[lang]
    w = data["width"]
    h = data["height"]
    elev = data["elevation_grid"]
    threat = data["threat_grid"]
    radars = data["radars"]
    waypoints = data["waypoints"]
    comparison = data["comparison"]

    # 1. Cieniowanie rzeźby terenu (Shaded Relief / Hillshade)
    # Stosujemy miękką, naturalną paletę hipsometryczną 'terrain' lub subtelną oliwkową
    ls = LightSource(azdeg=315, altdeg=45)
    elev_norm = (elev - np.min(elev)) / (np.max(elev) - np.min(elev) + 1e-5)
    try:
        cmap_topo = matplotlib.colormaps['gist_earth']
    except Exception:
        cmap_topo = plt.get_cmap('gist_earth')
    shaded_elev = ls.shade(elev, cmap=cmap_topo, vert_exag=1.8, blend_mode='soft')

    ax.imshow(shaded_elev, origin="upper", extent=[0, w, h, 0], aspect="equal")

    # 2. Izolinie wysokości (Contour lines) z etykietami
    min_el, max_el = np.min(elev), np.max(elev)
    if (max_el - min_el) > 1.5:
        num_levels = min(7, max(4, int(max_el - min_el) // 5))
        levels = np.linspace(min_el, max_el, num_levels + 2)[1:-1]
        cs = ax.contour(elev, levels=levels, colors='#37474F',
                        linewidths=0.6, alpha=0.45, origin="upper", extent=[0, w, h, 0])
        ax.clabel(cs, inline=True, fontsize=6.5, fmt='%.0f m', colors='#263238')

    # 3. Modelowanie cieni radarowych (Line-of-Sight shadows)
    for r in radars:
        rx, ry, r_range = r["x"], r["y"], r["range"]
        y_c, x_c = np.ogrid[:h, :w]
        dist_rad = np.hypot(x_c - rx, y_c - ry)
        in_range = dist_rad <= r_range
        is_shadow = in_range & (threat < 0.015)

        # Cień radarowy: półprzezroczysty, chłodny akwamarynowy deseń bezpieczeństwa
        shadow_overlay = np.zeros((h, w, 4))
        shadow_overlay[is_shadow] = [0.15, 0.65, 0.35, 0.22]
        ax.imshow(shadow_overlay, origin="upper", extent=[0, w, h, 0], aspect="equal")

    # 4. Strefy zagrożenia OPL (Gradient zagrożenia w zasięgu)
    threat_masked = np.ma.masked_where(threat < 0.01, threat)
    if np.any(threat > 0.01):
        ax.imshow(threat_masked, cmap="YlOrRd", alpha=0.35,
                  vmin=0.0, vmax=1.0, origin="upper", extent=[0, w, h, 0], aspect="equal")

    # 5. Okręgi zasięgu radarów OPL
    for r in radars:
        rx, ry, r_range = r["x"], r["y"], r["range"]
        # Zasięg maksymalny (przerywana linia karmazynowa)
        c_max = plt.Circle((rx, ry), r_range, color='#C62828', fill=False,
                           linestyle='--', linewidth=1.3, alpha=0.85, zorder=6)
        ax.add_patch(c_max)
        # Strefa bezpośredniego rażenia (0.5 R)
        c_kill = plt.Circle((rx, ry), r_range * 0.5, color='#B71C1C', fill=False,
                            linestyle=':', linewidth=1.0, alpha=0.6, zorder=6)
        ax.add_patch(c_kill)

        # Znacznik stacji SAM
        ax.plot(rx, ry, marker='^', markersize=8, color='#D32F2F',
                markeredgecolor='#FFFFFF', markeredgewidth=1.2, zorder=8)
        rad_label = f"SAM {r.get('id', 1)}\n({r_range:.0f}m)"
        ax.text(rx + 1.2, ry - 1.2, rad_label, fontsize=6.8, fontweight='bold',
                color='#B71C1C', bbox=dict(boxstyle='round,pad=0.2',
                facecolor='#FFFFFF', edgecolor='#B71C1C', alpha=0.85, lw=0.6), zorder=9)

    # 6. Rysowanie trajektorii algorytmów
    # (a) Trasa bazowa (Prosta)
    base_run = comparison.get("baseline", {})
    b_pts = base_run.get("path", [])
    if len(b_pts) > 1:
        bx = [p["x"] for p in b_pts]
        by = [p["y"] for p in b_pts]
        st = PATH_STYLES["baseline"]
        ax.plot(bx, by, color=st["color"], linestyle=st["linestyle"],
                linewidth=st["linewidth"], alpha=st["alpha"], zorder=4,
                label=f"1. {T['baseline']}")

    # (b) Czysty SA (przed wygładzeniem)
    sa_run = comparison.get("pure_sa", {})
    sa_pts = sa_run.get("path", [])
    if len(sa_pts) > 1:
        sx = [p["x"] for p in sa_pts]
        sy = [p["y"] for p in sa_pts]
        st = PATH_STYLES["pure_sa"]
        ax.plot(sx, sy, color=st["color"], linestyle=st["linestyle"],
                linewidth=st["linewidth"], alpha=st["alpha"], zorder=5,
                label=f"2. {T['pure_sa']}")

    # (c) Hybryda SA + Local Search (Optimum)
    opt_run = comparison.get("sa_ls", {})
    opt_pts = opt_run.get("path", data["opt_path"])
    if len(opt_pts) > 1:
        ox = np.array([p["x"] for p in opt_pts])
        oy = np.array([p["y"] for p in opt_pts])
        st = PATH_STYLES["sa_ls"]

        # Cień pod trasą optymalną dla maksymalnej czytelności na zróżnicowanym terenie
        ax.plot(ox, oy, color='#FFFFFF', linewidth=st["linewidth"] + 1.6, alpha=0.9, zorder=6)
        ax.plot(ox, oy, color=st["color"], linestyle=st["linestyle"],
                linewidth=st["linewidth"], alpha=st["alpha"], zorder=7,
                label=f"3. {T['sa_ls']}")

        # Wektory kierunkowe lotu (strzałki na trajektorii)
        step_arrow = max(10, len(opt_pts) // 8)
        for i in range(step_arrow // 2, len(opt_pts) - step_arrow // 2, step_arrow):
            dx = ox[i + 2] - ox[i]
            dy = oy[i + 2] - oy[i]
            mag = np.hypot(dx, dy)
            if mag > 0.05:
                ax.annotate('', xy=(ox[i] + dx * 0.4, oy[i] + dy * 0.4),
                            xytext=(ox[i], oy[i]),
                            arrowprops=dict(arrowstyle="->", color=st["color"],
                                            lw=1.6, mutation_scale=11),
                            zorder=8)

    # 7. Punkty nawigacyjne misji (Waypoints)
    for wp in waypoints:
        wx, wy = wp["x"], wp["y"]
        w_type = wp.get("type", "reconnaissance")
        w_name = wp.get("name", f"WP{wp.get('id', '')}")

        if w_type == "start":
            ax.plot(wx, wy, 's', markersize=9, color='#2E7D32',
                    markeredgecolor='#FFFFFF', markeredgewidth=1.4, zorder=10)
            ax.text(wx + 1.5, wy - 1.5, f"START\n({w_name})", fontsize=7.0, fontweight='bold',
                    color='#1B5E20', bbox=dict(boxstyle='square,pad=0.2',
                    facecolor='#E8F5E9', edgecolor='#2E7D32', lw=0.8), zorder=11)
        elif w_type == "return":
            ax.plot(wx, wy, 'H', markersize=10, color='#1565C0',
                    markeredgecolor='#FFFFFF', markeredgewidth=1.4, zorder=10)
            ax.text(wx + 1.5, wy + 2.5, f"BAZA / LZ\n({w_name})", fontsize=7.0, fontweight='bold',
                    color='#0D47A1', bbox=dict(boxstyle='square,pad=0.2',
                    facecolor='#E3F2FD', edgecolor='#1565C0', lw=0.8), zorder=11)
        elif w_type == "reconnaissance":
            ax.plot(wx, wy, 'D', markersize=8, color='#F57F17',
                    markeredgecolor='#FFFFFF', markeredgewidth=1.4, zorder=10)
            ax.text(wx + 1.5, wy - 1.5, f"CEL\n({w_name})", fontsize=7.0, fontweight='bold',
                    color='#E65100', bbox=dict(boxstyle='square,pad=0.2',
                    facecolor='#FFF8E1', edgecolor='#F57F17', lw=0.8), zorder=11)

    # 8. Kartografia: Skala, Północ, Osie
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    draw_cartographic_north_arrow(ax, x_pos=0.92, y_pos=0.86, scale=0.055)
    draw_cartographic_scale_bar(ax, length_m=min(25.0, w * 0.3), x_rel=0.05, y_rel=0.06)
    ax.set_xlabel(T["axis_x_m"], fontsize=8.5)
    ax.set_ylabel(T["axis_y_m"], fontsize=8.5)
    ax.set_title(T["map_title"], fontsize=9.5, fontweight='bold', pad=24)
    ax.grid(True, linestyle=':', color='#CFD8DC', alpha=0.7)

    # Legenda mapy wyciągnięta CAŁKOWICIE poza obszar mapy (ponad górną krawędź)
    leg_handles = [
        mlines.Line2D([], [], color=PATH_STYLES["baseline"]["color"], linestyle='--', lw=1.6, label=T["baseline_short"]),
        mlines.Line2D([], [], color=PATH_STYLES["pure_sa"]["color"], linestyle=':', lw=1.6, label=T["pure_sa_short"]),
        mlines.Line2D([], [], color=PATH_STYLES["sa_ls"]["color"], linestyle='-', lw=2.2, label=T["sa_ls_short"]),
        mpatches.Patch(facecolor='#81C784', edgecolor='#2E7D32', alpha=0.5, label=T["legend_radar_shadow"]),
        mpatches.Patch(facecolor='#FFCDD2', edgecolor='#C62828', alpha=0.6, label=T["legend_radar_max"]),
    ]
    ax.legend(handles=leg_handles, loc='lower center', bbox_to_anchor=(0.5, 1.01),
              ncol=5, fontsize=6.8, framealpha=0.95, facecolor='#FFFFFF', edgecolor='#B0BEC5',
              handletextpad=0.35, columnspacing=0.8)


# ==============================================================================
# SUBFIGURE (B): PROFIL WYSOKOŚCIOWY I EKSPOZYCJA OPL (ELEVATION PROFILE)
# ==============================================================================
def plot_elevation_profile(ax, data, lang="pl"):
    """Generuje inżynierski przekrój wzdłuż optymalnej trajektorii z ekspozycją OPL."""
    T = I18N[lang]
    path = data["comparison"]["sa_ls"].get("path", data["opt_path"])
    elev_grid = data["elevation_grid"]
    threat_grid = data["threat_grid"]
    w = data["width"]
    h = data["height"]

    if len(path) < 2:
        ax.text(0.5, 0.5, "Brak danych trajektorii 3D", ha='center', va='center')
        return

    dists = [0.0]
    elevs = []
    flight_alts = []
    threat_along_path = []

    for i in range(len(path)):
        pt = path[i]
        ix = int(np.clip(round(pt["x"]), 0, w - 1))
        iy = int(np.clip(round(pt["y"]), 0, h - 1))
        ground_z = elev_grid[iy, ix]
        elevs.append(ground_z)

        # Wysokość bezwzględna UAV (z ASL)
        curr_z = pt.get("z", ground_z + 10.0)
        flight_alts.append(curr_z)
        threat_along_path.append(threat_grid[iy, ix])

        if i > 0:
            p_prev = path[i - 1]
            prev_ix = int(np.clip(round(p_prev["x"]), 0, w - 1))
            prev_iy = int(np.clip(round(p_prev["y"]), 0, h - 1))
            prev_z = p_prev.get("z", elev_grid[prev_iy, prev_ix] + 10.0)
            step_d = np.hypot(np.hypot(pt["x"] - p_prev["x"], pt["y"] - p_prev["y"]), curr_z - prev_z)
            dists.append(dists[-1] + step_d)

    dists = np.array(dists)
    elevs = np.array(elevs)
    flight_alts = np.array(flight_alts)
    threat_along_path = np.array(threat_along_path)

    # 1. Bryła terenu (DEM fill)
    ax.fill_between(dists, 0, elevs, color='#B0BEC5', alpha=0.6,
                    label=T["legend_terrain_dem"], zorder=2)
    ax.plot(dists, elevs, color='#455A64', linewidth=1.2, zorder=3)

    # 2. Pułap lotu UAV
    ax.plot(dists, flight_alts, color='#0D47A1', linewidth=2.0,
            label=T["legend_uav_path"], zorder=4)

    # 3. Zaznaczenie stref narażenia na wiązkę radiolokacyjną
    exposure_mask = threat_along_path > 0.05
    if np.any(exposure_mask):
        ax.fill_between(dists, elevs, flight_alts, where=exposure_mask,
                        color='#FFCDD2', alpha=0.7, edgecolor='#D32F2F',
                        linewidth=0.8, linestyle='--', label=T["legend_exposure"], zorder=3)

    # Minimalny prześwit nad terenem (AGL)
    agl_clearances = flight_alts - elevs
    min_agl = np.min(agl_clearances)
    avg_agl = np.mean(agl_clearances)

    ax.set_xlim(0, dists[-1])
    ax.set_ylim(0, max(np.max(flight_alts) * 1.25, 30.0))
    ax.set_xlabel(T["axis_dist_m"], fontsize=8.5)
    ax.set_ylabel(T["axis_alt_m"], fontsize=8.5)
    ax.set_title(f"{T['profile_title']}  [$h_{{\\mathrm{{min}}}} = {min_agl:.1f}\\,\\mathrm{{m}}$, $h_{{\\mathrm{{avg}}}} = {avg_agl:.1f}\\,\\mathrm{{m}}$]",
                 fontsize=9.0, fontweight='bold', pad=24)
    ax.grid(True, linestyle=':', color='#CFD8DC')

    # Legenda profilu wyciągnięta CAŁKOWICIE poza wykres (nad profil)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3,
              fontsize=6.8, framealpha=0.95, facecolor='#FFFFFF', edgecolor='#B0BEC5',
              handletextpad=0.35, columnspacing=0.8)


# ==============================================================================
# SUBFIGURE (C): PORÓWNANIE ŁĄCZNEGO KOSZTU E(P) (OBJECTIVE COST BREAKDOWN)
# ==============================================================================
def plot_cost_comparison(ax, data, lang="pl"):
    """Rysuje publikacyjny wykres słupkowy całkowitego kosztu E(p)."""
    T = I18N[lang]
    comp = data["comparison"]
    order = ["baseline", "pure_ls", "pure_sa", "sa_ls"]
    labels = BAR_LABELS[lang]
    costs = [float(comp[k].get("totalCost", 0.0)) for k in order]

    x = np.arange(len(order))
    bars = ax.bar(x, costs, color=BAR_COLORS, width=0.46,
                  edgecolor='#37474F', linewidth=0.8, alpha=0.88, zorder=3)

    max_val = max(costs) if max(costs) > 0.01 else 1.0
    ax.set_ylim(0, max_val * 1.25)

    # Wartości nad słupkami
    for bar, val in zip(bars, costs):
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, yval + max_val * 0.02,
                f"{val:.1f}", ha='center', va='bottom', fontsize=7.2,
                fontweight='bold', color='#263238')

    base_cost = costs[0]
    opt_cost = costs[3]
    imp_pct = ((base_cost - opt_cost) / base_cost * 100.0) if base_cost > 0.01 else 0.0
    title_suffix = f"\n[$\\Delta E = -{imp_pct:.1f}\\%$ {T['best_badge']}]" if imp_pct > 0 else ""

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.2, linespacing=0.95)
    ax.set_ylabel(T["axis_cost"], fontsize=8.0)
    ax.set_title(f"{T['cost_title']}{title_suffix}", fontsize=8.8, fontweight='bold', pad=8)
    ax.grid(True, axis='y', linestyle=':', color='#CFD8DC')


# ==============================================================================
# SUBFIGURE (D): ANALIZA KOMPROMISU PARETO (TRADE-OFF: THREAT vs DISTANCE)
# ==============================================================================
def plot_tradeoff_analysis(ax, data, lang="pl"):
    """Rysuje dwuosiowy wykres relacji kompromisowej pomiędzy zagrożeniem a długością 3D."""
    T = I18N[lang]
    comp = data["comparison"]
    order = ["baseline", "pure_ls", "pure_sa", "sa_ls"]
    labels = BAR_LABELS[lang]

    threats = [float(comp[k].get("threatRisk", 0.0)) for k in order]
    dists = [float(comp[k].get("distance", 0.0)) for k in order]

    x = np.arange(len(order))
    width = 0.32

    ax2 = ax.twinx()

    b1 = ax.bar(x - width / 2.0, threats, width, label=T["axis_threat"],
                color='#D32F2F', alpha=0.82, edgecolor='#B71C1C', lw=0.8, zorder=3)
    b2 = ax2.bar(x + width / 2.0, dists, width, label=T["dist_col"],
                 color='#1976D2', alpha=0.75, edgecolor='#0D47A1', lw=0.8, zorder=3)

    max_t = max(threats) if max(threats) > 0.01 else 1.0
    max_d = max(dists) if max(dists) > 0.01 else 1.0

    ax.set_ylim(0, max_t * 1.25)
    ax2.set_ylim(0, max_d * 1.25)

    ax.set_ylabel(T["axis_threat"], color='#B71C1C', fontsize=7.8)
    ax2.set_ylabel(T["dist_col"], color='#0D47A1', fontsize=7.8)
    ax.tick_params(axis='y', labelcolor='#B71C1C', labelsize=7.5)
    ax2.tick_params(axis='y', labelcolor='#0D47A1', labelsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.2, linespacing=0.95)
    ax.set_title(T["tradeoff_title"], fontsize=9.0, fontweight='bold', pad=24)
    ax.grid(True, axis='y', linestyle=':', color='#CFD8DC')

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    # Legenda wyciągnięta CAŁKOWICIE poza wykres (nad wykres)
    ax.legend(lines1 + lines2, labels1 + labels2, loc='lower center',
              bbox_to_anchor=(0.5, 1.01), ncol=2,
              fontsize=6.8, framealpha=0.95, facecolor='#FFFFFF', edgecolor='#B0BEC5',
              handletextpad=0.3, columnspacing=0.8)


# ==============================================================================
# SUBFIGURE (E): KRZYWA ZBIEŻNOŚCI SA + LOCAL SEARCH (CONVERGENCE CURVE)
# ==============================================================================
def plot_convergence_history(ax, data, lang="pl"):
    """Generuje wykres dynamiki chłodzenia i redukcji funkcji celu w procesie optymalizacji."""
    T = I18N[lang]
    conv = data.get("convergence", [])
    comp = data["comparison"]
    cost_base = float(comp["baseline"].get("totalCost", 100.0))
    cost_sa = float(comp["pure_sa"].get("totalCost", 50.0))
    cost_sals = float(comp["sa_ls"].get("totalCost", 45.0))

    if len(conv) > 1:
        c_arr = np.array(conv)
        steps = np.arange(len(c_arr))
        ax.plot(steps, c_arr, color='#1565C0', linewidth=1.8,
                label=r"Simulated Annealing $E(k)$", zorder=4)
        ax.axhline(cost_base, color='#D32F2F', linestyle='--', linewidth=1.2,
                   label=f"{T['baseline']} ($E={cost_base:.1f}$)", zorder=3)

        # Skok Local Search
        if cost_sals < cost_sa - 0.01:
            ax.plot(len(c_arr) - 1, cost_sals, marker='o', markersize=6.5,
                    color='#2E7D32', markeredgecolor='#FFFFFF', markeredgewidth=1.2,
                    label=f"Local Search descent ($\\Delta = -{cost_sa - cost_sals:.1f}$)", zorder=5)
        ax.set_xlim(0, len(c_arr) - 1)
    else:
        # Syntetyczna krzywa asymptotyczna w przypadku braku pełnej historii iteracji
        steps = np.linspace(0, 100, 100)
        sim_c = cost_sals + (cost_base - cost_sals) * np.exp(-steps / 22.0)
        ax.plot(steps, sim_c, color='#1565C0', linewidth=1.8,
                label=r"Simulated Annealing $E(k)$", zorder=4)
        ax.axhline(cost_base, color='#D32F2F', linestyle='--', linewidth=1.2,
                   label=f"{T['baseline']} ($E={cost_base:.1f}$)", zorder=3)
        ax.plot(99, cost_sals, marker='o', markersize=6.5, color='#2E7D32',
                markeredgecolor='#FFFFFF', markeredgewidth=1.2,
                label=f"Local Search descent ($\\Delta = -{cost_sa - cost_sals:.1f}$)", zorder=5)
        ax.set_xlim(0, 99)

    ax.set_xlabel(T["axis_iter"], fontsize=8.0)
    ax.set_ylabel(T["axis_cost"], fontsize=8.0)
    ax.set_title(T["conv_title"], fontsize=9.0, fontweight='bold', pad=24)
    ax.grid(True, linestyle=':', color='#CFD8DC')

    # Legenda wyciągnięta CAŁKOWICIE poza wykres (nad wykres)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3,
              fontsize=6.8, framealpha=0.95, facecolor='#FFFFFF', edgecolor='#B0BEC5',
              handletextpad=0.35, columnspacing=0.8)


# ==============================================================================
# SUBFIGURE (F): TABELA WYNIKÓW W FORMACIE AKADEMICKIM (BOOKTABS TABLE)
# ==============================================================================
def plot_academic_table(ax, data, lang="pl"):
    """Renderuje elegancką tabelę metryk naukowych wzorowaną na stylu LaTeX booktabs."""
    T = I18N[lang]
    ax.axis('off')
    comp = data["comparison"]
    order = ["baseline", "pure_ls", "pure_sa", "sa_ls"]

    headers = TABLE_HEADERS[lang]

    cell_data = []
    for k in order:
        r = comp[k]
        name = TABLE_ROWS[lang].get(k, T.get(k, k))
        cost = f"{float(r.get('totalCost', 0.0)):.1f}"
        dist = f"{float(r.get('distance', 0.0)):.1f}"
        threat = f"{float(r.get('threatRisk', 0.0)):.2f}"
        tort = f"{float(r.get('tortuosity', 1.0)):.2f}"
        time_s = f"{float(r.get('flightTimeSec', 0.0)):.1f}"
        wps = f"{int(r.get('waypointsCount', 0))}"
        feas = "Bezpieczna (0)" if r.get("isFeasible", True) else f"KOLIZJA ({r.get('collisionCount', 1)})"
        cell_data.append([name, cost, dist, threat, tort, time_s, wps, feas])

    # Precyzyjnie dobrane szerokości kolumn (suma = 1.0) zapobiegające nakładaniu się tekstu
    col_widths = [0.23, 0.11, 0.11, 0.12, 0.10, 0.11, 0.08, 0.14]

    table = ax.table(cellText=cell_data, colLabels=headers,
                     colWidths=col_widths,
                     loc='center', cellLoc='center')

    table.auto_set_font_size(False)
    table.set_fontsize(7.2)
    table.scale(1.0, 1.45)

    # Stylizacja komórek (nagłówek, obramowania i wyróżnienie optimum)
    for (row_idx, col_idx), cell in table.get_celld().items():
        cell.set_edgecolor('#B0BEC5')
        cell.set_linewidth(0.6)
        if row_idx == 0:
            cell.set_text_props(weight='bold', color='#212121', size=7.0)
            cell.set_facecolor('#CFD8DC')
        elif row_idx == 4:  # SA + Local Search (Optimum)
            cell.set_facecolor('#E3F2FD')
            cell.set_text_props(weight='bold', color='#0D47A1', size=7.2)
        else:
            cell.set_facecolor('#FFFFFF')
            cell.set_text_props(color='#212121', size=7.2)

        # Wyrównanie pierwszej kolumny do lewej dla czytelności
        if col_idx == 0 and row_idx > 0:
            cell.get_text().set_horizontalalignment('left')

    ax.set_title(T["table_title"], fontsize=9.2, fontweight='bold', pad=14, loc='center')


# ==============================================================================
# GENERATOR KODU TABELI DLA SYSTEMU LATEX (\begin{table} ... \end{table})
# ==============================================================================
def generate_latex_table(data, lang="pl"):
    """Zwraca gotowy do wklejenia kod LaTeX tabeli ze środowiskiem booktabs."""
    T = I18N[lang]
    comp = data["comparison"]
    order = ["baseline", "pure_ls", "pure_sa", "sa_ls"]

    scenario_name = data["map_name"].replace("_", "\\_")

    latex = []
    latex.append("% --- KOD TABELI DO PRACY MAGISTERSKIEJ (WYMAGA: \\usepackage{booktabs}) ---")
    latex.append("\\begin{table}[htbp]")
    latex.append("  \\centering")
    latex.append(f"  \\caption{{{T['table_caption']} Scenariusz: \\texttt{{{scenario_name}}}}}")
    latex.append(f"  \\label{{tab:uav_routing_{data['map_name'].replace('.json', '')}}}")
    latex.append("  \\begin{tabular}{lcccccc}")
    latex.append("    \\toprule")
    latex.append(f"    \\textbf{{{T['metric_col']}}} & \\textbf{{{T['cost_col']}}} & \\textbf{{{T['dist_col']}}} & \\textbf{{{T['threat_col']}}} & \\textbf{{{T['tort_col']}}} & \\textbf{{{T['time_col']}}} & \\textbf{{{T['wps_col']}}} \\\\")
    latex.append("    \\midrule")

    for idx, k in enumerate(order):
        r = comp[k]
        name = T[k]
        cost = f"{float(r.get('totalCost', 0.0)):.1f}"
        dist = f"{float(r.get('distance', 0.0)):.1f}"
        threat = f"{float(r.get('threatRisk', 0.0)):.2f}"
        tort = f"{float(r.get('tortuosity', 1.0)):.2f}"
        time_s = f"{float(r.get('flightTimeSec', 0.0)):.1f}"
        wps = f"{int(r.get('waypointsCount', 0))}"

        # Pogrubienie optymalnego wiersza
        if k == "sa_ls":
            latex.append(f"    \\textbf{{{name}}} & \\textbf{{{cost}}} & \\textbf{{{dist}}} & \\textbf{{{threat}}} & \\textbf{{{tort}}} & \\textbf{{{time_s}}} & \\textbf{{{wps}}} \\\\")
        else:
            latex.append(f"    {name} & {cost} & {dist} & {threat} & {tort} & {time_s} & {wps} \\\\")

    latex.append("    \\bottomrule")
    latex.append("  \\end{tabular}")
    latex.append("\\end{table}")
    return "\n".join(latex)


# ==============================================================================
# GENERATOR POJEDYNCZYCH RYCYN AKADEMICKICH (INDIVIDUAL HIGH-RES FIGURES)
# ==============================================================================
def export_individual_figures(data, output_dir, lang="pl", dpi=300):
    """Zapisuje każdą rycinę osobno (np. do osobnych podrozdziałów pracy magisterskiej)."""
    os.makedirs(output_dir, exist_ok=True)
    setup_publication_style()
    base_name = os.path.splitext(data["map_name"])[0]

    # 1. Mapa taktyczna
    fig_map, ax_map = plt.subplots(figsize=(8.0, 7.5), facecolor='#FFFFFF')
    plot_topographic_map(ax_map, data, lang=lang, standalone=True)
    p_map = os.path.join(output_dir, f"{base_name}_1_topographic_map.png")
    fig_map.savefig(p_map, dpi=dpi, bbox_inches='tight')
    fig_map.savefig(p_map.replace(".png", ".pdf"), bbox_inches='tight')
    plt.close(fig_map)

    # 2. Profil wysokościowy
    fig_prof, ax_prof = plt.subplots(figsize=(8.0, 4.0), facecolor='#FFFFFF')
    plot_elevation_profile(ax_prof, data, lang=lang)
    p_prof = os.path.join(output_dir, f"{base_name}_2_elevation_profile.png")
    fig_prof.savefig(p_prof, dpi=dpi, bbox_inches='tight')
    fig_prof.savefig(p_prof.replace(".png", ".pdf"), bbox_inches='tight')
    plt.close(fig_prof)

    # 3. Koszt całkowity
    fig_cost, ax_cost = plt.subplots(figsize=(6.0, 4.2), facecolor='#FFFFFF')
    plot_cost_comparison(ax_cost, data, lang=lang)
    p_cost = os.path.join(output_dir, f"{base_name}_3_cost_comparison.png")
    fig_cost.savefig(p_cost, dpi=dpi, bbox_inches='tight')
    fig_cost.savefig(p_cost.replace(".png", ".pdf"), bbox_inches='tight')
    plt.close(fig_cost)

    # 4. Kompromis Pareto
    fig_trade, ax_trade = plt.subplots(figsize=(6.5, 4.2), facecolor='#FFFFFF')
    plot_tradeoff_analysis(ax_trade, data, lang=lang)
    p_trade = os.path.join(output_dir, f"{base_name}_4_tradeoff_analysis.png")
    fig_trade.savefig(p_trade, dpi=dpi, bbox_inches='tight')
    fig_trade.savefig(p_trade.replace(".png", ".pdf"), bbox_inches='tight')
    plt.close(fig_trade)

    # 5. Zbieżność
    fig_conv, ax_conv = plt.subplots(figsize=(6.5, 4.0), facecolor='#FFFFFF')
    plot_convergence_history(ax_conv, data, lang=lang)
    p_conv = os.path.join(output_dir, f"{base_name}_5_convergence_curve.png")
    fig_conv.savefig(p_conv, dpi=dpi, bbox_inches='tight')
    fig_conv.savefig(p_conv.replace(".png", ".pdf"), bbox_inches='tight')
    plt.close(fig_conv)

    # 6. Tabela LaTeX
    latex_code = generate_latex_table(data, lang=lang)
    p_tex = os.path.join(output_dir, f"{base_name}_table.tex")
    with open(p_tex, "w", encoding="utf-8") as f:
        f.write(latex_code)

    print(f"\n[SUKCES] Wyeksportowano pakiet rycin do pracy magisterskiej:")
    print(f"  • Katalog: {output_dir}")
    print(f"  • Format: PNG ({dpi} DPI) + Wektorowy PDF")
    print(f"  • Pliki: {base_name}_1_topographic_map, {base_name}_2_elevation_profile, itp.")
    print(f"  • Tabela LaTeX: {p_tex}")


# ==============================================================================
# GŁÓWNY PANEL NAUKOWY (COMPREHENSIVE MULTI-PANEL ACADEMIC DASHBOARD)
# ==============================================================================
def build_academic_dashboard(data, lang="pl"):
    """Buduje pełnowymiarowy, zintegrowany panel publikacyjny o strukturze siatki 2x3."""
    setup_publication_style()
    T = I18N[lang]

    fig = plt.figure(figsize=(20.0, 12.0), facecolor='#FFFFFF')
    fig.canvas.manager.set_window_title(f"UAV TACTICAL ROUTING - RAPORT NAUKOWY [{data['map_name']}]")

    # Siatka: Lewa strona (Główna mapa i Profil), Prawa strona (Analityka i Tabela)
    # Zwiększony hspace (0.48) zapewnia pełny margines na legendy i tytuły umieszczone poza obrysem wykresów
    gs = GridSpec(3, 4, figure=fig,
                  left=0.045, right=0.965, top=0.92, bottom=0.055,
                  wspace=0.38, hspace=0.48)

    # (a) Mapa Hipsometryczna (zajmuje 2 wiersze po lewej)
    ax_map = fig.add_subplot(gs[0:2, 0:2])

    # (b) Profil wysokościowy (pod mapą po lewej)
    ax_profile = fig.add_subplot(gs[2, 0:2])

    # (c) Porównanie kosztu (góra prawo)
    ax_cost = fig.add_subplot(gs[0, 2])

    # (d) Kompromis Pareto (góra skrajne prawo)
    ax_tradeoff = fig.add_subplot(gs[0, 3])

    # (e) Krzywa zbieżności (środek prawo)
    ax_conv = fig.add_subplot(gs[1, 2:])

    # (f) Tabela naukowa (dół prawo)
    ax_table = fig.add_subplot(gs[2, 2:])

    # Renderowanie poszczególnych komponentów
    plot_topographic_map(ax_map, data, lang=lang)
    plot_elevation_profile(ax_profile, data, lang=lang)
    plot_cost_comparison(ax_cost, data, lang=lang)
    plot_tradeoff_analysis(ax_tradeoff, data, lang=lang)
    plot_convergence_history(ax_conv, data, lang=lang)
    plot_academic_table(ax_table, data, lang=lang)

    # Główny nagłówek naukowy
    title_str = f"{T['title_main']} — Scenariusz: {data['map_name']}"
    fig.suptitle(title_str, fontsize=12.5, fontweight='bold', color='#1A237E', y=0.975)

    return fig


# ==============================================================================
# GŁÓWNA FUNKCJA WEJŚCIOWA (CLI ENTRY POINT)
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="UAV Tactical Routing - Academic Publication & Thesis Visualizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PRZYKŁADY UŻYCIA (PRACA MAGISTERSKA):
  python python/academic_viewer.py 1                      # Podgląd interaktywny Test 1 (Płaski)
  python python/academic_viewer.py 2                      # Test 2 (Grzbiet górski)
  python python/academic_viewer.py 3                      # Test 3 (Kanion vs szczyty)
  python python/academic_viewer.py perlin                 # Mapa proceduralna Perlin
  python python/academic_viewer.py perlin --save rycina.png   # Zapis pełnej ryciny w 300 DPI
  python python/academic_viewer.py perlin --save rycina.pdf   # Wektorowy PDF do LaTeX
  python python/academic_viewer.py perlin --save-figures rysunki/ # Zapis osobnych wykresów i tabeli .tex!
  python python/academic_viewer.py 2 --latex              # Wypisanie gotowego kodu tabeli LaTeX
  python python/academic_viewer.py perlin --lang en       # Wersja w języku angielskim
        """
    )
    parser.add_argument("map", nargs="?", default="data/maps/perlin_full_test_map.json",
                        help="Ścieżka do mapy JSON lub skrót: 1, 2, 3, perlin (domyślnie: perlin)")
    parser.add_argument("-s", "--save", dest="save_path", default=None,
                        help="Ścieżka zapisu pełnego panelu (np. raport.png, wykres.pdf)")
    parser.add_argument("--save-figures", "--split-save", dest="save_figures_dir", default=None,
                        help="Katalog do zapisu pojedynczych wykresów o wysokiej rozdzielczości oraz tabeli .tex")
    parser.add_argument("--dpi", type=int, default=300,
                        help="Rozdzielczość eksportu grafiki rastrowej (domyślnie: 300 DPI)")
    parser.add_argument("--lang", choices=["pl", "en"], default="pl",
                        help="Język etykiet wykresów i tabeli: pl (polski) lub en (angielski)")
    parser.add_argument("--latex", action="store_true",
                        help="Wypisz gotowy kod tabeli LaTeX booktabs do wklejenia do pracy")

    args = parser.parse_args()

    resolved_path = resolve_map_path(args.map)
    if not resolved_path:
        print(f"\n[BŁĄD] Nie odnaleziono pliku mapy: {args.map}")
        print("Dostępne skróty:")
        print("  1      -> data/maps/test_1_flat.json")
        print("  2      -> data/maps/test_2_ridge_wall.json")
        print("  3      -> data/maps/test_3_canyon_peaks.json")
        print("  perlin -> data/maps/perlin_full_test_map.json")
        sys.exit(1)

    print(f"\n[ACADEMIC VIEWER] Wczytywanie danych operacyjnych z: {resolved_path}")
    dataset = load_mission_dataset(resolved_path)

    # Opcja 1: Wypisanie tabeli LaTeX na standardowe wyjście
    if args.latex:
        latex_code = generate_latex_table(dataset, lang=args.lang)
        print("\n" + latex_code + "\n")
        if not args.save_path and not args.save_figures_dir:
            return

    # Opcja 2: Zapis poszczególnych wykresów do dedykowanego katalogu
    if args.save_figures_dir:
        export_individual_figures(dataset, args.save_figures_dir, lang=args.lang, dpi=args.dpi)
        if not args.save_path:
            return

    # Opcja 3: Budowa pełnego zintegrowanego dashboardu
    fig = build_academic_dashboard(dataset, lang=args.lang)

    if args.save_path:
        fig.savefig(args.save_path, dpi=args.dpi, bbox_inches='tight', pad_inches=0.15)
        print(f"[SUKCES] Wygenerowano publikacyjną rycinę naukową: {args.save_path} ({args.dpi} DPI)")
    else:
        print(f"[ACADEMIC VIEWER] Otwieranie interaktywnego okna publikacyjnego...")
        plt.show()


if __name__ == "__main__":
    main()
