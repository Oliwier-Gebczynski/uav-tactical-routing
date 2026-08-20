import json                                                                                                                              
import os                                                                                                                                
import sys                                                                                                                               
import numpy as np                                                                                                                       
import matplotlib                                                                                                                        
                                                                                                                                            
matplotlib.use('Qt5Agg')                                                                                                                 
import matplotlib.pyplot as plt                                                                                                          
from matplotlib.colors import ListedColormap, BoundaryNorm, LightSource                                                                  
import matplotlib.patches as mpatches                                                                                                    
                                                                                                                                            
MAP_FILE = "data/maps/perlin_full_test_map.json"                                                                                         
                                                                                                                                            
if not os.path.exists(MAP_FILE):                                                                                                         
    MAP_FILE = "../data/maps/perlin_full_test_map.json"                                                                                  
    if not os.path.exists(MAP_FILE):                                                                                                     
        print("Błąd: Nie znaleziono pliku mapy!")                                                                                        
        sys.exit(1)                                                                                                                      
                                                                                                                                            
print(f"Wczytywanie mapy z {MAP_FILE}...")                                                                                               
with open(MAP_FILE, "r", encoding="utf-8") as f:                                                                                         
    data = json.load(f)                                                                                                                  
                                                                                                                                            
width = data.get("width", 100)                                                                                                           
height = data.get("height", 100)                                                                                                         
raw_cells = data.get("cells", [])                                                                                                        
radars = data.get("radars", [])                                                                                                          
                                                                                                                                            
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
                                                                                                                                                                                                                                
fig, axes = plt.subplots(2, 2, figsize=(14, 12))                                                                                         
fig.canvas.manager.set_window_title("Planowanie Tras UAV - Analiza Taktyczna i Fuzja Map")                                               
                                                                                                                                            
cmap_terrain = ListedColormap(COLORS)                                                                                                    
norm_terrain = BoundaryNorm(boundaries=[-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], ncolors=5)                                                       
                                                                                                                      
axes[0, 0].imshow(terrain_grid, cmap=cmap_terrain, norm=norm_terrain, origin="upper")                                                    
axes[0, 0].set_title("1. Typy Terenu (Land Cover)", fontsize=11, fontweight="bold")                                                      
patches = [mpatches.Patch(color=COLORS[i], label=LABELS[i]) for i in range(len(COLORS))]                                                 
axes[0, 0].legend(handles=patches, loc="upper left", bbox_to_anchor=(0.0, -0.08), ncol=3, fontsize=8)                                    
                                                                                                              
im1 = axes[0, 1].imshow(elevation_grid, cmap="terrain", origin="upper")                                                                  
axes[0, 1].set_title("2. Ukształtowanie Terenu (DEM m n.p.m.)", fontsize=11, fontweight="bold")                                          
fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)                                                                               

im2 = axes[1, 0].imshow(threat_grid, cmap="hot_r", origin="upper", vmin=0.0, vmax=1.0)
axes[1, 0].set_title("3. Strefy Zagrożenia OPL (Maskowanie Terenem)", fontsize=11, fontweight="bold")
fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04, label="Poziom Zagrożenia")

for r in radars:
    rx, ry, r_range = r["x"], r["y"], r["range"]
    circle = plt.Circle((rx, ry), r_range, color='red', fill=False, linestyle='--', linewidth=1.2, alpha=0.7)
    axes[1, 0].add_patch(circle)
    axes[1, 0].plot(rx, ry, 'r^', markersize=8, markeredgecolor='black')

ax_fusion = axes[1, 1]
ax_fusion.set_title("4. Zintegrowana Mapa Taktyczna (Fuzja 1 + 2 + 3)", fontsize=11, fontweight="bold")

terrain_rgb = cmap_terrain(norm_terrain(terrain_grid))[:, :, :3]

ls = LightSource(azdeg=315, altdeg=45)
shaded_terrain = ls.shade_rgb(terrain_rgb, elevation=elevation_grid, blend_mode='overlay', vert_exag=1.5)
ax_fusion.imshow(shaded_terrain, origin="upper")

contours = ax_fusion.contour(elevation_grid, levels=6, colors='black', alpha=0.35, linewidths=0.6, origin="upper")
ax_fusion.clabel(contours, inline=True, fontsize=7, fmt='%1.0fm')

threat_rgba = plt.cm.Reds(threat_grid)

threat_rgba[..., 3] = np.clip(threat_grid * 0.65, 0.0, 0.65)
ax_fusion.imshow(threat_rgba, origin="upper")

for r in radars:
    rx, ry, r_range = r["x"], r["y"], r["range"]
    circle = plt.Circle((rx, ry), r_range, color='darkred', fill=False, linestyle='--', linewidth=1.5, alpha=0.85)
    ax_fusion.add_patch(circle)
    ax_fusion.plot(rx, ry, 'r^', markersize=9, markeredgecolor='black', markeredgewidth=1.2)

ax_fusion.plot([], [], 'r^', markeredgecolor='black', label="Radar OPL")
ax_fusion.legend(loc="upper right", fontsize=8)

plt.tight_layout()
print("Wyświetlanie okna z mapami...")
plt.show()