import json
import os
import sys
import numpy as np
import matplotlib

matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm, LightSource
import matplotlib.patches as mpatches

# Obsługa argumentów wiersza poleceń
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

# Wyszukiwanie pliku w bieżącym katalogu lub katalogu nadrzędnym
if not os.path.exists(MAP_FILE):
    alt_path = os.path.join("..", MAP_FILE)
    if os.path.exists(alt_path):
        MAP_FILE = alt_path
    else:
        print(f"Błąd: Nie znaleziono pliku mapy: {MAP_FILE}")
        print("Dostępne skróty:")
        print("  python viewer.py 1       -> Test 1: Płaski teren (koło)")
        print("  python viewer.py 2       -> Test 2: Grzbiet górski (cień)")
        print("  python viewer.py 3       -> Test 3: Kanion vs Szczyty")
        print("  python viewer.py perlin  -> Mapa proceduralna Perlin")
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

# Panel 1: Typy Terenu
axes[0, 0].imshow(terrain_grid, cmap=cmap_terrain, norm=norm_terrain, origin="upper")
axes[0, 0].set_title(f"1. Typy Terenu (Land Cover) [{width}x{height}]", fontsize=11, fontweight="bold")
patches = [mpatches.Patch(color=COLORS[i], label=LABELS[i]) for i in range(len(COLORS))]
axes[0, 0].legend(handles=patches, loc="upper left", bbox_to_anchor=(0.0, -0.08), ncol=3, fontsize=8)

# Panel 2: Ukształtowanie Terenu
im1 = axes[0, 1].imshow(elevation_grid, cmap="terrain", origin="upper")
axes[0, 1].set_title("2. Ukształtowanie Terenu (DEM m n.p.m.)", fontsize=11, fontweight="bold")
fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

# Panel 3: Strefy Zagrożenia OPL
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

# Panel 4: Fuzja Map + Trasa UAV i Punkty Kontrolne
ax_fusion = axes[1, 1]
ax_fusion.set_title("4. Fuzja Taktyczna: Teren + Radary + Trasa UAV", fontsize=11, fontweight="bold")

terrain_rgb = cmap_terrain(norm_terrain(terrain_grid))[:, :, :3]
ls = LightSource(azdeg=315, altdeg=45)
shaded_terrain = ls.shade_rgb(terrain_rgb, elevation=elevation_grid, blend_mode='overlay', vert_exag=1.5)
ax_fusion.imshow(shaded_terrain, origin="upper")

# Poziomice
if np.max(elevation_grid) - np.min(elevation_grid) > 1.0:
    contours = ax_fusion.contour(elevation_grid, levels=6, colors='black', alpha=0.35, linewidths=0.6, origin="upper")
    ax_fusion.clabel(contours, inline=True, fontsize=7, fmt='%1.0fm')

# Jaskrawa nakładka strefy zagrożenia OPL (Mocne krycie)
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

# Rysowanie szczegółowej ścieżki lotu UAV (kratka po kratce)
if len(path) > 0:
    px = [p["x"] for p in path]
    py = [p["y"] for p in path]

    # Zaznaczenie każdego odwiedzonego kwadratu siatki jako mały punkt
    ax_fusion.scatter(px, py, color='#00E5FF', s=12, alpha=0.7, zorder=6, label=f"Odwiedzone komórki ({len(path)})")
    # Ciągła linia trajektorii lotu
    ax_fusion.plot(px, py, color='#00E5FF', linewidth=2.4, linestyle='-', zorder=5, label="Wstępna Trasa UAV")

# Rysowanie punktów kontrolnych misji (Waypoints)
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
    else:  # Reconnaissance / Transit
        ax_fusion.plot(wx, wy, 'D', color='#FFD600', markersize=10, markeredgecolor='black', markeredgewidth=1.5, zorder=7)
        ax_fusion.text(wx + 1.5, wy - 1.5, f"CEL {wp.get('id', '')}\n({w_name})", color='black', fontsize=8, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFD600', alpha=0.9, edgecolor='black'), zorder=8)

# HUD / Box ze statystykami trasy
if path_stats:
    dist = path_stats.get("totalDistance", 0.0)
    threat_exp = path_stats.get("totalThreatExposure", 0.0)
    max_th = path_stats.get("maxThreatLevel", 0.0) * 100.0
    cells_cnt = path_stats.get("totalVisitedCells", len(path))

    stats_str = f"Dystans: {dist:.1f} m\nOdwiedzone komórki: {cells_cnt}\nEkspozycja na OPL: {threat_exp:.2f}\nMax Zagrożenie: {max_th:.0f}%"
    ax_fusion.text(0.02, 0.03, stats_str, transform=ax_fusion.transAxes, fontsize=8.5, fontweight='bold',
                   color='white', bbox=dict(boxstyle='round,pad=0.4', facecolor='#212121', alpha=0.85, edgecolor='#00E5FF', linewidth=1.5),
                   zorder=10)

ax_fusion.plot([], [], 'r^', markersize=9, markeredgecolor='black', markeredgewidth=1.2, label="Radar OPL")
ax_fusion.plot([], [], color='#D50000', linestyle='--', linewidth=1.6, label="Zasięg Teoretyczny (R_max)")
ax_fusion.legend(loc="upper right", fontsize=7.5)

plt.tight_layout()
print(f"Wyświetlanie okna z mapą [{map_name}]...")
plt.show()