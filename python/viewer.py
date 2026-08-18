import json
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches

import matplotlib
matplotlib.use('Qt5Agg') 
import matplotlib.pyplot as plt

MAP_FILE = "../data/maps/perlin_full_test_map.json"

if not os.path.exists(MAP_FILE):
    MAP_FILE = "data/maps/perlin_full_test_map.json"
    if not os.path.exists(MAP_FILE):
        print(f"Błąd: Nie znaleziono pliku mapy!")
        sys.exit(1)

print(f"Wczytywanie mapy z {MAP_FILE}...")
with open(MAP_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

width = data.get("width", 100)
height = data.get("height", 100)
raw_cells = data.get("cells", [])

if len(raw_cells) > 0 and isinstance(raw_cells[0], list):
    flat_cells = [cell for row in raw_cells for cell in row]
else:
    flat_cells = raw_cells

terrain_grid = np.zeros((height, width), dtype=int)
elevation_grid = np.zeros((height, width), dtype=float)
concealment_grid = np.zeros((height, width), dtype=float)

TERRAIN_MAPPING = {
    "water": 0,
    "grass": 1,
    "forest": 2,
    "road": 3,
    "building": 4
}

COLORS = ["#1E88E5", "#7CB342", "#1B5E20", "#212121", "#757575"]
LABELS = ["Woda (Water)", "Łąka (Grass)", "Las (Forest)", "Droga (Road)", "Budynek (Building)"]

for idx, cell in enumerate(flat_cells):
    if idx >= width * height:
        break
    x = idx % width
    y = idx // width

    if isinstance(cell, dict):
        t_type = str(cell.get("terrain", "grass")).lower()
        terrain_grid[y, x] = TERRAIN_MAPPING.get(t_type, 1)
        elevation_grid[y, x] = float(cell.get("elevation", 0.0))
        concealment_grid[y, x] = float(cell.get("concealment", 0.0))

fig, axes = plt.subplots(1, 2, figsize=(15, 7))
fig.canvas.manager.set_window_title("Podgląd Środowiska Misji UAV - UAVPlanner")

cmap_terrain = ListedColormap(COLORS)
norm_terrain = BoundaryNorm(boundaries=[-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], ncolors=5)

im0 = axes[0].imshow(terrain_grid, cmap=cmap_terrain, norm=norm_terrain, origin="upper")
axes[0].set_title("Typy Terenu (Biomy & Infrastruktura)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("X (metry)")
axes[0].set_ylabel("Y (metry)")

patches = [mpatches.Patch(color=COLORS[i], label=LABELS[i]) for i in range(len(COLORS))]
axes[0].legend(handles=patches, bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0.)

im1 = axes[1].imshow(elevation_grid, cmap="YlOrRd", origin="upper")
axes[1].set_title("Ukształtowanie Terenu (Wysokość całkowita)", fontsize=13, fontweight="bold")
axes[1].set_xlabel("X (metry)")
axes[1].set_ylabel("Y (metry)")

cbar = fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
cbar.set_label("Wysokość (metry n.p.m.)", rotation=270, labelpad=15, fontweight="bold")

plt.tight_layout()
print("Wyświetlanie okna z mapami...")
plt.show()