import json
import os
import sys
import numpy as np
import matplotlib

matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm, LightSource
import matplotlib.patches as mpatches
from ..paths import resolve_input_path

MAP_SHORTCUTS = {
    "1": "data/maps/test_1_flat.json",
    "2": "data/maps/test_2_ridge_wall.json",
    "3": "data/maps/test_3_canyon_peaks.json",
    "p": "data/maps/perlin_full_test_map.json",
    "perlin": "data/maps/perlin_full_test_map.json",
}

if len(sys.argv) > 1:
    arg = sys.argv[1].strip()
    if arg in MAP_SHORTCUTS:
        MAP_FILE = MAP_SHORTCUTS[arg]
    else:
        MAP_FILE = arg
else:
    MAP_FILE = "data/maps/perlin_full_test_map.json"

MAP_FILE = str(resolve_input_path(MAP_FILE))
if not os.path.exists(MAP_FILE):
    print(f"Błąd: Nie znaleziono pliku mapy: {MAP_FILE}")
    print("Dostępne skróty: python/main.py view 1|2|3|perlin")
    sys.exit(1)

map_name = os.path.basename(MAP_FILE)
print(f"Wczytywanie mapy: {MAP_FILE}...")
with open(MAP_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

width = data.get("width", 100)
height = data.get("height", 100)
raw_cells = data.get("cells", [])
radars = data.get("radars", [])
mission = data.get("mission", {})
waypoints = mission.get("waypoints", [])
path = data.get("path", [])
path_stats = data.get("pathStats", {})

if len(raw_cells) > 0 and isinstance(raw_cells[0], list):
    flat_cells = [cell for row in raw_cells for cell in row]
else:
    flat_cells = raw_cells

terrain_grid = np.zeros((height, width), dtype=int)
elevation_grid = np.zeros((height, width), dtype=float)
threat_grid = np.zeros((height, width), dtype=float)

TERRAIN_MAPPING = {"water": 0, "grass": 1, "forest": 2, "road": 3, "building": 4}
COLORS = ["#1E88E5", "#7CB342", "#1B5E20", "#212121", "#757575"]
LABELS = ["Woda", "Łąka", "Las", "Droga", "Budynek"]

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

fig, axes = plt.subplots(2, 2, figsize=(15, 13))
fig.canvas.manager.set_window_title(f"Planowanie Tras UAV - Reprezentacja Trasy [{map_name}]")

cmap_terrain = ListedColormap(COLORS)
norm_terrain = BoundaryNorm(boundaries=[-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], ncolors=5)

axes[0, 0].imshow(terrain_grid, cmap=cmap_terrain, norm=norm_terrain, origin="upper")
axes[0, 0].set_title(f"1. Typy Terenu (Land Cover) [{width}x{height}]", fontsize=11, fontweight="bold", pad=8)
patches = [mpatches.Patch(color=COLORS[i], label=LABELS[i]) for i in range(len(COLORS))]
axes[0, 0].legend(handles=patches, loc="upper right", fontsize=7.5, framealpha=0.85)

im1 = axes[0, 1].imshow(elevation_grid, cmap="terrain", origin="upper")
axes[0, 1].set_title("2. Ukształtowanie Terenu (DEM m n.p.m.)", fontsize=11, fontweight="bold")
fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

im2 = axes[1, 0].imshow(threat_grid, cmap="hot_r", origin="upper", vmin=0.0, vmax=1.0)
axes[1, 0].set_title("3. Strefy Zagrożenia OPL (Maskowanie Terenem)", fontsize=11, fontweight="bold")
fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04, label="Poziom Zagrożenia")

for r in radars:
    rx, ry, r_range = r["x"], r["y"], r["range"]
    circle = plt.Circle((rx, ry), r_range, color='red', fill=False, linestyle='--', linewidth=1.4, alpha=0.85)
    axes[1, 0].add_patch(circle)
    axes[1, 0].plot(rx, ry, 'r^', markersize=9, markeredgecolor='black', markeredgewidth=1.2)
    axes[1, 0].text(rx + 1.2, ry - 1.2, f"R{r.get('id', '')}", color='black', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='yellow', alpha=0.8, edgecolor='black', linewidth=0.7))

ax_fusion = axes[1, 1]
ax_fusion.set_title("4. Fuzja Taktyczna: Teren + Radary + Trasa UAV", fontsize=11, fontweight="bold")

terrain_rgb = cmap_terrain(norm_terrain(terrain_grid))[:, :, :3]
ls = LightSource(azdeg=315, altdeg=45)
shaded_terrain = ls.shade_rgb(terrain_rgb, elevation=elevation_grid, blend_mode='overlay', vert_exag=1.5)
ax_fusion.imshow(shaded_terrain, origin="upper")

if np.max(elevation_grid) - np.min(elevation_grid) > 1.0:
    contours = ax_fusion.contour(elevation_grid, levels=6, colors='black', alpha=0.35, linewidths=0.6, origin="upper")
    ax_fusion.clabel(contours, inline=True, fontsize=7, fmt='%1.0fm')

threat_rgba = plt.cm.YlOrRd(threat_grid)
alpha_channel = np.zeros_like(threat_grid)
mask = threat_grid > 0.001
alpha_channel[mask] = np.clip(0.70 + threat_grid[mask] * 0.25, 0.70, 0.95)
threat_rgba[..., 3] = alpha_channel
ax_fusion.imshow(threat_rgba, origin="upper")

for r in radars:
    rx, ry, r_range = r["x"], r["y"], r["range"]
    circle = plt.Circle((rx, ry), r_range, color='#D50000', fill=False, linestyle='--', linewidth=1.6, alpha=0.9)
    ax_fusion.add_patch(circle)
    ax_fusion.plot(rx, ry, 'r^', markersize=10, markeredgecolor='black', markeredgewidth=1.4)
    ax_fusion.text(rx + 1.2, ry - 1.2, f"R{r.get('id', '')}", color='black', fontsize=10, fontweight='heavy',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.8, edgecolor='black', linewidth=0.8))

comparison = data.get("comparison", {})
baseline_run = comparison.get("baseline", {})
pure_ls_run = comparison.get("pure_ls", {})
pure_sa_run = comparison.get("pure_sa", {})

path_base = baseline_run.get("path", [])
if len(path_base) > 1:
    bx = [p["x"] for p in path_base]
    by = [p["y"] for p in path_base]
    ax_fusion.plot(bx, by, color='#FFB300', linewidth=1.8, linestyle='--', alpha=0.85, zorder=4, label="1. Prosta (Brak)")

path_ls = pure_ls_run.get("path", [])
if len(path_ls) > 1:
    lx = [p["x"] for p in path_ls]
    ly = [p["y"] for p in path_ls]
    ax_fusion.plot(lx, ly, color='#FF9100', linewidth=2.0, linestyle='-.', alpha=0.9, zorder=5, label="2. Local Search")

path_sa = pure_sa_run.get("path", []) if len(pure_sa_run.get("path", [])) > 0 else path
if len(path_sa) > 0:
    px = [p["x"] for p in path_sa]
    py = [p["y"] for p in path_sa]

    ax_fusion.scatter(px, py, color='#00E5FF', s=12, alpha=0.7, zorder=6)
    ax_fusion.plot(px, py, color='#00E5FF', linewidth=2.4, linestyle='-', zorder=6, label="3. Trasa SA")

for wp in waypoints:
    wx, wy = wp["x"], wp["y"]
    w_type = wp.get("type", "reconnaissance")
    w_name = wp.get("name", f"WP{wp.get('id', '')}")

    if w_type == "start":
        ax_fusion.plot(wx, wy, 'go', markersize=12, markeredgecolor='white', markeredgewidth=2, zorder=7)
        ax_fusion.text(wx + 1.5, wy - 1.5, f"START\n({w_name})", color='white', fontsize=8, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.25', facecolor='#2E7D32', alpha=0.9, edgecolor='white'), zorder=8)
    elif w_type == "return":
        ax_fusion.plot(wx, wy, 'bs', markersize=12, markeredgecolor='white', markeredgewidth=2, zorder=7)
        ax_fusion.text(wx + 1.5, wy + 2.5, f"POWRÓT\n({w_name})", color='white', fontsize=8, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.25', facecolor='#1565C0', alpha=0.9, edgecolor='white'), zorder=8)
    elif w_type == "transit":
        ax_fusion.plot(wx, wy, 'o', color='#00E5FF', markersize=6, markeredgecolor='white', markeredgewidth=1.0, zorder=7)
    else:
        ax_fusion.plot(wx, wy, 'D', color='#FFD600', markersize=10, markeredgecolor='black', markeredgewidth=1.5, zorder=7)
        ax_fusion.text(wx + 1.5, wy - 1.5, f"CEL {wp.get('id', '')}\n({w_name})", color='black', fontsize=8, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFD600', alpha=0.9, edgecolor='black'), zorder=8)

if path_stats:
    dist = path_stats.get("totalDistance", 0.0)
    threat_exp = path_stats.get("effectiveThreatExposure", path_stats.get("totalThreatExposure", 0.0))
    raw_threat = path_stats.get("totalThreatExposure", threat_exp)
    max_th = path_stats.get("maxThreatLevel", 0.0) * 100.0
    cells_cnt = path_stats.get("totalVisitedCells", len(path))
    total_cost = path_stats.get("totalCost", None)
    is_feasible = path_stats.get("isFeasible", True)

    if total_cost is not None:
        feasibility_tag = "BEZPIECZNA" if is_feasible else "KOLIZJA!"
        stats_str = (f"Koszt E(Path): {total_cost:.1f} [{feasibility_tag}]\n"
                     f"Dystans: {dist:.1f} m | Komórki: {cells_cnt}\n"
                     f"Ryzyko OPL (efekt.): {threat_exp:.2f} (surowe: {raw_threat:.2f})\n"
                     f"Max Zagrożenie: {max_th:.0f}%")
    else:
        stats_str = f"Dystans: {dist:.1f} m\nOdwiedzone komórki: {cells_cnt}\nEkspozycja na OPL: {threat_exp:.2f}\nMax Zagrożenie: {max_th:.0f}%"

    edge_color = '#00E5FF' if is_feasible else '#FF1744'
    ax_fusion.text(0.02, 0.03, stats_str, transform=ax_fusion.transAxes, fontsize=8.5, fontweight='bold',
                   color='white', bbox=dict(boxstyle='round,pad=0.4', facecolor='#212121', alpha=0.85, edgecolor=edge_color, linewidth=1.5),
                   zorder=10)

ax_fusion.plot([], [], 'r^', markersize=9, markeredgecolor='black', markeredgewidth=1.2, label="Radar OPL")
ax_fusion.plot([], [], color='#D50000', linestyle='--', linewidth=1.6, label="Zasięg Teoretyczny (R_max)")
ax_fusion.legend(loc="upper right", fontsize=7.5)

plt.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.06, wspace=0.25, hspace=0.28)
print(f"Wyświetlanie okna z mapą [{map_name}]...")
plt.show()