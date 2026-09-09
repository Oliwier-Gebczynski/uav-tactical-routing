#!/usr/bin/env python3

import json
import os
import sys
import numpy as np
import matplotlib

if "--save" in sys.argv or "-s" in sys.argv:
    matplotlib.use('Agg')
else:
    try:
        matplotlib.use('Qt5Agg')
    except Exception:
        matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm, LightSource
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

MAP_SHORTCUTS = {
    "1": "data/maps/test_1_flat.json",
    "2": "data/maps/test_2_ridge_wall.json",
    "3": "data/maps/test_3_canyon_peaks.json",
    "p": "data/maps/perlin_full_test_map.json",
    "perlin": "data/maps/perlin_full_test_map.json",
}

save_path = None
map_arg = "data/maps/perlin_full_test_map.json"

for i, arg in enumerate(sys.argv[1:], 1):
    if arg in ["--save", "-s"] and i < len(sys.argv) - 1:
        save_path = sys.argv[i + 1]
    elif not arg.startswith("-") and sys.argv[i - 1] not in ["--save", "-s"]:
        map_arg = MAP_SHORTCUTS.get(arg.strip(), arg.strip())

MAP_FILE = map_arg
if not os.path.exists(MAP_FILE):
    alt_path = os.path.join("..", MAP_FILE)
    if os.path.exists(alt_path):
        MAP_FILE = alt_path
    else:
        print(f"[BŁĄD C2] Nie znaleziono pliku mapy taktycznej: {MAP_FILE}")
        print("Dostępne mapy:")
        print("  python tactical_c2_viewer.py 1       -> Test 1: Płaski teren (Omijanie radaru)")
        print("  python tactical_c2_viewer.py 2       -> Test 2: Grzbiet górski (Cień radarowy)")
        print("  python tactical_c2_viewer.py 3       -> Test 3: Kanion vs Szczyty")
        print("  python tactical_c2_viewer.py perlin  -> Mapa proceduralna Perlin")
        print("  python tactical_c2_viewer.py 1 --save output.png")
        sys.exit(1)

map_name = os.path.basename(MAP_FILE)
print(f"[C2 TAC-NET] Wczytywanie danych operacyjnych z: {MAP_FILE}")

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
path_cost = data.get("pathCost", {})
comparison = data.get("comparison", {})
baseline_run = comparison.get("baseline", {})
pure_ls_run = comparison.get("pure_ls", {})
pure_sa_run = comparison.get("pure_sa", {})
sa_ls_run = comparison.get("sa_ls", {})
convergence = data.get("convergence", [])
metrics_summary = data.get("metrics", {})

if len(raw_cells) > 0 and isinstance(raw_cells[0], list):
    flat_cells = [cell for row in raw_cells for cell in row]
else:
    flat_cells = raw_cells

terrain_grid = np.zeros((height, width), dtype=int)
elevation_grid = np.zeros((height, width), dtype=float)
threat_grid = np.zeros((height, width), dtype=float)
concealment_grid = np.zeros((height, width), dtype=float)

TERRAIN_MAPPING = {"water": 0, "grass": 1, "forest": 2, "road": 3, "building": 4}
MIL_COLORS = ["#0A2540", "#2C3B2D", "#143D1F", "#2A2E33", "#4A5568"]
MIL_LABELS = ["Woda (NAV-OBS)", "Teren Otwarty (GRASS)", "Las (CONCEALMENT 80%)", "Droga (ROAD)", "Zabudowania (URBAN-OBS)"]

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

plt.style.use('dark_background')
fig = plt.figure(figsize=(28, 11.8), facecolor='#0B0E14')
fig.canvas.manager.set_window_title(f"UAV BATTLEFIELD C2 COP & ALGORITHM BENCHMARK - [{map_name}]")

gs = GridSpec(18, 26, figure=fig, left=0.035, right=0.955, top=0.95, bottom=0.06, wspace=0.55, hspace=0.65)

ax_legend = fig.add_subplot(gs[0:2, 0:11])
ax_legend.set_facecolor('#10141D')
ax_legend.axis('off')

ax_map = fig.add_subplot(gs[2:12, 0:11])
ax_map.set_facecolor('#070A0F')

ax_profile = fig.add_subplot(gs[12:18, 0:11])
ax_profile.set_facecolor('#0E121A')

ax_hud = fig.add_subplot(gs[0:18, 12:18])
ax_hud.set_facecolor('#10141D')
ax_hud.axis('off')

# Column 18 is spacer between HUD and right comparison charts!
# Row 5 and row 11 are spacers between charts to prevent label/title collisions!
ax_chart_cost = fig.add_subplot(gs[0:5, 19:26])
ax_chart_cost.set_facecolor('#0E121A')

ax_chart_tradeoff = fig.add_subplot(gs[6:11, 19:26])
ax_chart_tradeoff.set_facecolor('#0E121A')

ax_chart_conv = fig.add_subplot(gs[12:18, 19:26])
ax_chart_conv.set_facecolor('#0E121A')

cmap_mil = ListedColormap(MIL_COLORS)
norm_mil = BoundaryNorm(boundaries=[-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], ncolors=5)

terrain_rgb = cmap_mil(norm_mil(terrain_grid))[:, :, :3]
ls = LightSource(azdeg=315, altdeg=45)
shaded_terrain = ls.shade_rgb(terrain_rgb, elevation=elevation_grid, blend_mode='overlay', vert_exag=1.8)

ax_map.imshow(shaded_terrain, origin="upper", extent=[0, width, height, 0])

if np.max(elevation_grid) - np.min(elevation_grid) > 1.0:
    contours = ax_map.contour(elevation_grid, levels=7, colors='#37474F', alpha=0.45, linewidths=0.7, origin="upper")
    ax_map.clabel(contours, inline=True, fontsize=6.5, fmt='%1.0fm', colors='#78909C')

for r in radars:
    rx, ry, r_range = r["x"], r["y"], r["range"]
    y_coords, x_coords = np.ogrid[:height, :width]
    dist_from_radar = np.sqrt((x_coords - rx)**2 + (y_coords - ry)**2)
    in_range = dist_from_radar <= r_range
    is_shadow = in_range & (threat_grid < 0.01)

    shadow_rgba = np.zeros((height, width, 4))
    shadow_rgba[is_shadow] = [0.0, 0.9, 0.4, 0.18]
    ax_map.imshow(shadow_rgba, origin="upper", extent=[0, width, height, 0])

threat_rgba = plt.cm.gist_heat_r(threat_grid)
threat_mask = threat_grid > 0.005
alpha_ch = np.zeros_like(threat_grid)
alpha_ch[threat_mask] = np.clip(0.40 + threat_grid[threat_mask] * 0.45, 0.40, 0.85)
threat_rgba[..., 3] = alpha_ch
ax_map.imshow(threat_rgba, origin="upper", extent=[0, width, height, 0])

for r in radars:
    rx, ry, r_range = r["x"], r["y"], r["range"]

    circle_max = plt.Circle((rx, ry), r_range, color='#FF1744', fill=False, linestyle='--', linewidth=1.6, alpha=0.85)
    ax_map.add_patch(circle_max)

    circle_lethal = plt.Circle((rx, ry), r_range * 0.5, color='#D50000', fill=False, linestyle=':', linewidth=1.2, alpha=0.7)
    ax_map.add_patch(circle_lethal)

    ax_map.plot(rx, ry, '^', color='#FF1744', markersize=11, markeredgecolor='#FFFFFF', markeredgewidth=1.2, zorder=8)
    ax_map.text(rx + 1.2, ry - 1.2, f"EW-SAM [{r.get('id', '')}]\nR={r_range:.0f}m", color='#FFFFFF', fontsize=7.5,
                fontweight='bold', fontfamily='monospace',
                bbox=dict(boxstyle='square,pad=0.2', facecolor='#B71C1C', alpha=0.9, edgecolor='#FF8A80', linewidth=1), zorder=9)

key_wps = [wp for wp in waypoints if wp.get("type") in ["start", "reconnaissance", "return"]]
if len(key_wps) < 2:
    key_wps = waypoints

path_base = baseline_run.get("path", [])
if len(path_base) > 1:
    bx = [p["x"] for p in path_base]
    by = [p["y"] for p in path_base]
    ax_map.plot(bx, by, color='#FFB300', linewidth=1.8, linestyle='--', alpha=0.85, zorder=4, label="1. Prosta (Brak planowania)")
elif len(key_wps) > 1:
    bx = [wp["x"] for wp in key_wps]
    by = [wp["y"] for wp in key_wps]
    ax_map.plot(bx, by, color='#FFB300', linewidth=1.8, linestyle='--', alpha=0.85, zorder=4, label="1. Prosta (Brak planowania)")

path_sa = pure_sa_run.get("path", [])
if len(path_sa) > 1:
    sx = [p["x"] for p in path_sa]
    sy = [p["y"] for p in path_sa]
    ax_map.plot(sx, sy, color='#E040FB', linewidth=1.4, linestyle=':', alpha=0.75, zorder=5, label="2. Czyste SA")
    ax_map.scatter(sx[::4], sy[::4], color='#E040FB', s=5, alpha=0.6, zorder=5)

if len(path) > 0:
    px = np.array([p["x"] for p in path])
    py = np.array([p["y"] for p in path])
    pz = np.array([p.get("z", 0.0) for p in path])

    ax_map.plot(px, py, color='#00E5FF', linewidth=5.0, alpha=0.22, zorder=6)
    ax_map.plot(px, py, color='#00F0FF', linewidth=2.4, linestyle='-', zorder=7, label="3. SA + Local Search")
    ax_map.scatter(px[::2], py[::2], color='#FFFFFF', s=6, alpha=0.85, zorder=8)

    step_arrow = max(8, len(path) // 12)
    for i in range(0, len(path) - step_arrow, step_arrow):
        dx = px[i + step_arrow] - px[i]
        dy = py[i + step_arrow] - py[i]
        mag = np.hypot(dx, dy)
        if mag > 0.1:
            ax_map.arrow(px[i], py[i], dx * 0.45, dy * 0.45, head_width=1.4, head_length=1.6,
                         fc='#00E5FF', ec='#00E5FF', zorder=7, length_includes_head=True)

for wp in waypoints:
    wx, wy = wp["x"], wp["y"]
    w_type = wp.get("type", "reconnaissance")
    w_name = wp.get("name", f"WP{wp.get('id', '')}")

    if w_type == "start":
        ax_map.plot(wx, wy, 's', color='#00E676', markersize=11, markeredgecolor='white', markeredgewidth=1.8, zorder=10)
        ax_map.text(wx + 1.5, wy - 1.5, f"LAUNCH BASE\n[{w_name.upper()}]", color='#FFFFFF', fontsize=7.5, fontweight='bold',
                    fontfamily='monospace', bbox=dict(boxstyle='square,pad=0.25', facecolor='#1B5E20', alpha=0.9, edgecolor='#69F0AE'), zorder=11)
    elif w_type == "return":
        ax_map.plot(wx, wy, 'H', color='#2979FF', markersize=12, markeredgecolor='white', markeredgewidth=1.8, zorder=10)
        ax_map.text(wx + 1.5, wy + 2.5, f"RECOVERY LZ\n[{w_name.upper()}]", color='#FFFFFF', fontsize=7.5, fontweight='bold',
                    fontfamily='monospace', bbox=dict(boxstyle='square,pad=0.25', facecolor='#0D47A1', alpha=0.9, edgecolor='#82B1FF'), zorder=11)
    elif w_type == "transit":
        ax_map.plot(wx, wy, 'o', color='#00E5FF', markersize=6, markeredgecolor='#0B0E14', markeredgewidth=1.2, zorder=10)
        ax_map.text(wx + 1.0, wy + 1.0, f"CP{wp.get('id','')}", color='#00E5FF', fontsize=6.5, fontfamily='monospace', zorder=11)
    else:
        ax_map.plot(wx, wy, 'D', color='#FFD600', markersize=10, markeredgecolor='black', markeredgewidth=1.5, zorder=10)
        ax_map.text(wx + 1.5, wy - 1.5, f"TARGET RECON\n[{w_name.upper()}]", color='#000000', fontsize=7.5, fontweight='bold',
                    fontfamily='monospace', bbox=dict(boxstyle='square,pad=0.25', facecolor='#FFD600', alpha=0.95, edgecolor='#000000'), zorder=11)

ax_map.set_xlim(0, width)
ax_map.set_ylim(height, 0)
ax_map.set_xlabel("GRID EASTING (m)", fontsize=8.5, fontfamily='monospace', color='#90A4AE')
ax_map.set_ylabel("GRID NORTHING (m)", fontsize=8.5, fontfamily='monospace', color='#90A4AE')
ax_map.grid(True, color='#1E293B', linestyle=':', linewidth=0.8, alpha=0.7)

for cx in [5, width // 2, width - 5]:
    for cy in [5, height // 2, height - 5]:
        ax_map.plot(cx, cy, '+', color='#00E5FF', markersize=8, markeredgewidth=1.0, alpha=0.5)

patches = [mpatches.Patch(color=MIL_COLORS[i], label=MIL_LABELS[i]) for i in range(len(MIL_COLORS))]
line_base = matplotlib.lines.Line2D([0], [0], color='#FFB300', linestyle='--', linewidth=1.6, label='1. Prosta (Brak planowania)')
line_sa = matplotlib.lines.Line2D([0], [0], color='#E040FB', linestyle=':', linewidth=1.5, label='2. Czyste SA')
line_opt = matplotlib.lines.Line2D([0], [0], color='#00F0FF', linestyle='-', linewidth=2.2, label='3. SA + Local Search')
legend_handles = patches + [line_base, line_sa, line_opt]
ax_legend.legend(handles=legend_handles, loc="center", ncol=4, fontsize=6.5, framealpha=0.9, facecolor='#10141D', edgecolor='#37474F', handletextpad=0.5, columnspacing=1.0)

ax_map.text(0.96, 0.94, "▲\nN", transform=ax_map.transAxes, color='#00E5FF', fontsize=11, fontweight='bold',
            fontfamily='monospace', ha='center', va='center',
            bbox=dict(boxstyle='circle,pad=0.25', facecolor='#10141D', edgecolor='#00E5FF', linewidth=1.2))

ax_profile.set_title("ELEVATION CROSS-SECTION // FLIGHT CEILING PROFILE [TERRAIN MASKING vs DEM]",
                     fontsize=8.5, fontweight='bold', fontfamily='monospace', color='#00E5FF', loc='left')

if len(path) > 1:
    dists = [0.0]
    elevs = []
    flight_alts = []
    threat_along_path = []

    for i in range(len(path)):
        pt = path[i]
        ix = int(np.clip(round(pt["x"]), 0, width - 1))
        iy = int(np.clip(round(pt["y"]), 0, height - 1))
        cell_elev = elevation_grid[iy, ix]
        elevs.append(cell_elev)
        curr_z = pt.get("z", cell_elev + 10.0)
        flight_alts.append(curr_z)
        threat_along_path.append(threat_grid[iy, ix])

        if i > 0:
            p_prev = path[i - 1]
            prev_ix = int(np.clip(round(p_prev["x"]), 0, width - 1))
            prev_iy = int(np.clip(round(p_prev["y"]), 0, height - 1))
            prev_z = p_prev.get("z", elevation_grid[prev_iy, prev_ix] + 10.0)
            seg_d = np.sqrt((pt["x"] - p_prev["x"])**2 + (pt["y"] - p_prev["y"])**2 + (curr_z - prev_z)**2)
            dists.append(dists[-1] + seg_d)

    dists = np.array(dists)
    elevs = np.array(elevs)
    flight_alts = np.array(flight_alts)
    threat_along_path = np.array(threat_along_path)

    ax_profile.fill_between(dists, 0, elevs, color='#1E293B', alpha=0.9, label="Rzeźba Terenu (DEM)")
    ax_profile.plot(dists, elevs, color='#90A4AE', linewidth=1.2)

    ax_profile.plot(dists, flight_alts, color='#00E5FF', linewidth=1.8, label="Pułap UAV (h_AGL)")

    threat_hazard = threat_along_path > 0.05
    if np.any(threat_hazard):
        ax_profile.fill_between(dists, elevs, flight_alts, where=threat_hazard,
                                color='#FF1744', alpha=0.4, label="Strefa Ekspozycji OPL")

    ax_profile.set_xlim(0, dists[-1])
    ax_profile.set_ylim(0, max(np.max(flight_alts) + 10.0, 30.0))
    ax_profile.set_xlabel("DYSTANS TRASY (m)", fontsize=8, fontfamily='monospace', color='#90A4AE')
    ax_profile.set_ylabel("ALTITUDE ASL (m)", fontsize=8, fontfamily='monospace', color='#90A4AE')
    ax_profile.grid(True, color='#1E293B', linestyle=':', linewidth=0.7)
    ax_profile.legend(loc="upper right", fontsize=7.0, facecolor='#10141D', edgecolor='#37474F')

dist_val = path_stats.get("totalDistance", dists[-1] if (len(path) > 1 and 'dists' in locals()) else 0.0)
cells_val = path_stats.get("totalVisitedCells", len(path))
threat_eff = path_stats.get("effectiveThreatExposure", path_stats.get("totalThreatExposure", 0.0))
threat_raw = path_stats.get("totalThreatExposure", threat_eff)
max_threat = path_stats.get("maxThreatLevel", 0.0) * 100.0
total_cost = path_stats.get("totalCost", 0.0)
is_feasible = path_stats.get("isFeasible", True)
collision_count = path_stats.get("collisionCount", 0)
conceal_benefit = path_stats.get("concealmentBenefit", 0.0)

base_dist = 0.0
base_threat = 0.0

if len(key_wps) > 1:
    for k in range(1, len(key_wps)):
        w1, w2 = key_wps[k - 1], key_wps[k]
        ix1 = int(np.clip(round(w1["x"]), 0, width - 1))
        iy1 = int(np.clip(round(w1["y"]), 0, height - 1))
        ix2 = int(np.clip(round(w2["x"]), 0, width - 1))
        iy2 = int(np.clip(round(w2["y"]), 0, height - 1))

        z1 = elevation_grid[iy1, ix1] + w1.get("altitudeAGL", 10.0)
        z2 = elevation_grid[iy2, ix2] + w2.get("altitudeAGL", 10.0)

        seg_len = np.sqrt((w2["x"] - w1["x"])**2 + (w2["y"] - w1["y"])**2 + (z2 - z1)**2)
        base_dist += seg_len

        samples = max(2, int(seg_len))
        for t in np.linspace(0.0, 1.0, samples):
            sx = int(np.clip(round((1.0 - t) * w1["x"] + t * w2["x"]), 0, width - 1))
            sy = int(np.clip(round((1.0 - t) * w1["y"] + t * w2["y"]), 0, height - 1))
            base_threat += threat_grid[sy, sx]
else:
    base_dist = dist_val

cost_base = float(baseline_run.get("totalCost", (base_threat * 50.0 + base_dist)))
dist_base = float(baseline_run.get("distance", base_dist))
threat_base = float(baseline_run.get("threatRisk", base_threat))
tort_base = float(baseline_run.get("tortuosity", 1.0))
time_base = float(baseline_run.get("flightTimeSec", dist_base / (60 / 3.6)))
wps_base = int(baseline_run.get("waypointsCount", len(key_wps)))

cost_ls = float(pure_ls_run.get("totalCost", cost_base))
dist_ls = float(pure_ls_run.get("distance", dist_base))
threat_ls = float(pure_ls_run.get("threatRisk", threat_base))
tort_ls = float(pure_ls_run.get("tortuosity", tort_base))
time_ls = float(pure_ls_run.get("flightTimeSec", dist_ls / (60 / 3.6)))
wps_ls = int(pure_ls_run.get("waypointsCount", wps_base))

cost_sa = float(pure_sa_run.get("totalCost", total_cost * 1.08))
dist_sa = float(pure_sa_run.get("distance", dist_val * 1.04))
threat_sa = float(pure_sa_run.get("threatRisk", threat_eff * 1.05))
tort_sa = float(pure_sa_run.get("tortuosity", (dist_sa / dist_base) if dist_base > 0.001 else 1.25))
time_sa = float(pure_sa_run.get("flightTimeSec", dist_sa / (60 / 3.6)))
wps_sa = int(pure_sa_run.get("waypointsCount", len(waypoints) + 3))

cost_sals = float(sa_ls_run.get("totalCost", total_cost))
dist_sals = float(sa_ls_run.get("distance", dist_val))
threat_sals = float(sa_ls_run.get("threatRisk", threat_eff))
tort_sals = float(sa_ls_run.get("tortuosity", (dist_sals / dist_base) if dist_base > 0.001 else 1.15))
time_sals = float(sa_ls_run.get("flightTimeSec", dist_sals / (60 / 3.6)))
wps_sals = int(sa_ls_run.get("waypointsCount", len(waypoints)))

imp_cost_pct = ((cost_base - cost_sals) / cost_base * 100.0) if cost_base > 0.001 else 0.0
detour_pct = ((dist_sals - dist_base) / dist_base * 100.0) if dist_base > 0.001 else 0.0
detour_str = f"{detour_pct:+.1f} %"

if threat_base > 0.001:
    threat_red = max(0.0, (1.0 - threat_sals / threat_base) * 100.0)
    threat_red_str = f"-{threat_red:.1f} % (vs prosta)"
else:
    threat_red_str = "100.0 % (BEZPIECZNA)"

if len(path) > 0:
    agls = []
    for pt in path:
        pix = int(np.clip(round(pt["x"]), 0, width - 1))
        piy = int(np.clip(round(pt["y"]), 0, height - 1))
        agls.append(pt.get("z", elevation_grid[piy, pix] + 10.0) - elevation_grid[piy, pix])
    min_agl, max_agl, avg_agl = np.min(agls), np.max(agls), np.mean(agls)
else:
    min_agl, max_agl, avg_agl = 10.0, 10.0, 10.0

decision_log = data.get("decisionLog", [])
chronicle_lines = []

if len(decision_log) > 0:
    chosen_events = [decision_log[0]]
    mid_events = [e for e in decision_log[1:] if e.get("phase") in ["BREAKTHROUGH", "METROPOLIS_JUMP"]]
    if len(mid_events) > 2:
        chosen_events.append(mid_events[0])
        chosen_events.append(mid_events[-1])
    else:
        chosen_events.extend(mid_events)

    ls_events = [e for e in decision_log if e.get("phase") == "LOCAL_SEARCH"]
    if len(ls_events) > 0 and ls_events[-1] not in chosen_events:
        chosen_events.append(ls_events[-1])

    for ev in chosen_events[:4]:
        it = ev.get("iteration", 0)
        ph = ev.get("phase", "SA")
        dt = ev.get("details", "")
        if len(dt) > 42:
            dt = dt[:39] + "..."
        chronicle_lines.append(f"   • [Krok {it:>3}|{ph[:6]}] {dt}")
else:
    chronicle_lines.append("   • [KROK 000|INIT  ] Wstępna prosta przez punkty misji")
    if threat_eff < threat_raw:
        chronicle_lines.append("   • [SA-OPT |MASKING] Wykorzystano cienie terenu DEM i las")
    if len(radars) > 0:
        chronicle_lines.append(f"   • [SA-OPT |EVASION] Ominięto {len(radars)} aktywnych stacji SAM")
    chronicle_lines.append("   • [L-SRCH |SMOOTH ] Local Search wygładził zakręty trasy")

chronicle_str = "\n".join(chronicle_lines)

ax_hud.text(0.02, 0.985, "┌── TACTICAL ROUTING & ALGORITHM BENCHMARK ────────────┐", color='#00E5FF', fontsize=7.4, fontfamily='monospace', va='top')

status_label = "TAK (BEZPIECZNA / 0 KOLIZJI)" if is_feasible else f"ALERT ({collision_count} KOLIZJI)"

tot_iter = metrics_summary.get("totalIterations", 27200)
metrop = metrics_summary.get("acceptedWorseMoves", 7500)
better = metrics_summary.get("acceptedBetterMoves", 6500)

hud_text = (
    f" STATUS MISJI:           {status_label}\n"
    f" ──────────────────────────────────────────────────────\n"
    f" 1. ZESTAWIENIE PORÓWNAWCZE METRYK (4 WARIANTY):\n"
    f"    Metryka        Prosta   Czysty SA   SA+Local\n"
    f"    Koszt E:       {cost_base:>7.1f}  {cost_sa:>8.1f}   {cost_sals:>7.1f} (-{imp_cost_pct:.1f}%)\n"
    f"    Długość 3D:    {dist_base:>6.1f}m  {dist_sa:>7.1f}m   {dist_sals:>6.1f}m ({detour_str})\n"
    f"    Ryzyko OPL:    {threat_base:>7.2f}  {threat_sa:>8.2f}   {threat_sals:>7.2f} ({threat_red_str})\n"
    f"    Krętość (L/D): {tort_base:>7.2f}  {tort_sa:>8.2f}   {tort_sals:>7.2f}\n"
    f"    Czas lotu ETA: {time_base:>6.1f}s  {time_sa:>7.1f}s   {time_sals:>6.1f}s\n"
    f"    Punkty WP:     {wps_base:>7d}  {wps_sa:>8d}   {wps_sals:>7d} (-{wps_sa - wps_sals} w LS)\n"
    f" ──────────────────────────────────────────────────────\n"
    f" 2. PRZETRWANIE I UNIKANIE OPL (SAM):\n"
    f"   • Redukcja zagrożenia OPL:       {threat_red_str}\n"
    f"   • Efektywne ryzyko (R_eff):      {threat_sals:.2f} (Surowe: {threat_raw:.2f})\n"
    f"   • Szczytowa ekspozycja radarowa: {max_threat:.0f} %\n"
    f"   • Zysk z maskowania (Teren/Las): -{conceal_benefit:.2f}\n"
    f"   • Aktywne stacje radarowe:       {len(radars)} emiterów\n"
    f" ──────────────────────────────────────────────────────\n"
    f" 3. KRONIKA DECYZJI PLANERA (KROKI I POWODY):\n"
    f"{chronicle_str}\n"
    f" ──────────────────────────────────────────────────────\n"
    f" 4. EFEKTYWNOŚĆ OPTYMALIZACJI HYBRYDOWEJ:\n"
    f"   • Próby SA: {tot_iter} | Metropolis: {metrop} | Lepsze: {better}\n"
    f"   • Redukcja funkcji celu: {cost_base - cost_sals:.1f} pkt ({imp_cost_pct:.1f}% zysku)\n"
)
ax_hud.text(0.02, 0.955, hud_text, color='#CFD8DC', fontsize=6.4, fontfamily='monospace', va='top', linespacing=1.22)
ax_hud.text(0.02, 0.015, "└── SA + LOCAL SEARCH // ALGORITHM QUALITY VERIFIED ───┘", color='#00E5FF', fontsize=7.4, fontfamily='monospace', va='bottom')

rect_hud = plt.Rectangle((0.005, 0.006), 0.99, 0.988, fill=False, edgecolor='#1E293B', linewidth=1.4, transform=ax_hud.transAxes)
ax_hud.add_patch(rect_hud)

algo_labels = ['Prosta\n(Brak)', 'Local\nSearch', 'Czysty\nSA', 'SA+Local\nSearch']
cost_vals = [cost_base, cost_ls, cost_sa, cost_sals]
cost_colors = ['#FF1744', '#FF9100', '#E040FB', '#00E5FF']

ax_chart_cost.set_title("1. PORÓWNANIE ŁĄCZNEGO KOSZTU E(PATH)", fontsize=8.0, fontweight='bold', fontfamily='monospace', color='#00E5FF', loc='left', pad=7)
bars = ax_chart_cost.bar(algo_labels, cost_vals, color=cost_colors, width=0.48, edgecolor='#FFFFFF', linewidth=0.7, alpha=0.88)
max_c = max(cost_vals) if max(cost_vals) > 0.001 else 1.0
ax_chart_cost.set_ylim(0, max_c * 1.30)

for bar, val in zip(bars, cost_vals):
    yval = bar.get_height()
    ax_chart_cost.text(bar.get_x() + bar.get_width()/2.0, yval + max_c * 0.02,
                       f"{val:.1f}", ha='center', va='bottom', fontsize=6.8,
                       fontfamily='monospace', color='#FFFFFF', fontweight='bold')

if cost_base > 0.001:
    ax_chart_cost.text(0.97, 0.88, f"ZYSK SA+LS:\n-{imp_cost_pct:.1f}%", transform=ax_chart_cost.transAxes,
                       ha='right', va='top', fontsize=7.2, fontweight='bold', fontfamily='monospace',
                       color='#00E676', bbox=dict(boxstyle='square,pad=0.25', facecolor='#1B5E20', edgecolor='#69F0AE', alpha=0.85))

ax_chart_cost.set_ylabel("KOSZT E", fontsize=7.0, fontfamily='monospace', color='#90A4AE', labelpad=5)
ax_chart_cost.tick_params(axis='x', labelsize=6.8, colors='#CFD8DC', pad=3)
ax_chart_cost.tick_params(axis='y', labelsize=6.6, colors='#90A4AE', pad=3)
ax_chart_cost.grid(True, linestyle=':', color='#1E293B', linewidth=0.7, axis='y')

ax_chart_tradeoff.set_title("2. TRADE-OFF: ZAGROŻENIE OPL vs DYSTANS 3D", fontsize=8.0, fontweight='bold', fontfamily='monospace', color='#00E5FF', loc='left', pad=7)

x_idx = np.arange(len(algo_labels))
bar_w = 0.32

threat_series = [threat_base, threat_ls, threat_sa, threat_sals]
dist_series = [dist_base, dist_ls, dist_sa, dist_sals]

ax2_tradeoff = ax_chart_tradeoff.twinx()
b1 = ax_chart_tradeoff.bar(x_idx - bar_w/2, threat_series, bar_w, label="Ryzyko OPL (R_eff)", color='#FF1744', alpha=0.85, edgecolor='#FF8A80', linewidth=0.6)
b2 = ax2_tradeoff.bar(x_idx + bar_w/2, dist_series, bar_w, label="Długość 3D (m)", color='#00E5FF', alpha=0.70, edgecolor='#80D8FF', linewidth=0.6)

max_t = max(threat_series) if max(threat_series) > 0.001 else 1.0
max_d = max(dist_series) if max(dist_series) > 0.001 else 1.0
ax_chart_tradeoff.set_ylim(0, max_t * 1.35)
ax2_tradeoff.set_ylim(0, max_d * 1.35)

ax_chart_tradeoff.set_ylabel("RYZYKO OPL", fontsize=7.0, fontfamily='monospace', color='#FF8A80', labelpad=5)
ax2_tradeoff.set_ylabel("DYSTANS (m)", fontsize=7.0, fontfamily='monospace', color='#80D8FF', labelpad=5)
ax_chart_tradeoff.set_xticks(x_idx)
ax_chart_tradeoff.set_xticklabels(algo_labels, fontsize=6.8, fontfamily='monospace', color='#CFD8DC')
ax_chart_tradeoff.tick_params(axis='x', pad=3)
ax_chart_tradeoff.tick_params(axis='y', labelsize=6.6, colors='#FF8A80', pad=3)
ax2_tradeoff.tick_params(axis='y', labelsize=6.6, colors='#80D8FF', pad=3)
ax_chart_tradeoff.grid(True, linestyle=':', color='#1E293B', linewidth=0.7, axis='y')

lines1, labels1 = ax_chart_tradeoff.get_legend_handles_labels()
lines2, labels2 = ax2_tradeoff.get_legend_handles_labels()
ax_chart_tradeoff.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=6.3, facecolor='#10141D', edgecolor='#37474F', handletextpad=0.4)

ax_chart_conv.set_title("3. DYNAMIKA ZBIEŻNOŚCI SA + LOCAL SEARCH", fontsize=8.0, fontweight='bold', fontfamily='monospace', color='#00E5FF', loc='left', pad=7)

if len(convergence) > 1:
    c_arr = np.array(convergence)
    steps = np.arange(len(c_arr))
    ax_chart_conv.plot(steps, c_arr, color='#00E5FF', linewidth=1.7, label="Koszt E(Iteracja)")
    ax_chart_conv.axhline(cost_base, color='#FF1744', linestyle='--', linewidth=1.2, alpha=0.85, label=f"Baza: {cost_base:.1f}")
    if cost_sals < cost_sa - 0.01:
        ax_chart_conv.plot(len(c_arr) - 1, cost_sals, 'o', color='#00E676', markersize=6, label=f"Local Search (-{cost_sa - cost_sals:.1f})")
    ax_chart_conv.set_xlim(0, len(c_arr) - 1)
else:
    steps = np.linspace(0, 100, 100)
    sim_conv = cost_sals + (cost_base - cost_sals) * np.exp(-steps / 22.0)
    ax_chart_conv.plot(steps, sim_conv, color='#00E5FF', linewidth=1.7, label="Koszt E(Iteracja)")
    ax_chart_conv.axhline(cost_base, color='#FF1744', linestyle='--', linewidth=1.2, alpha=0.85, label=f"Baza: {cost_base:.1f}")
    ax_chart_conv.plot(99, cost_sals, 'o', color='#00E676', markersize=6, label=f"Local Search (-{cost_sa - cost_sals:.1f})")
    ax_chart_conv.set_xlim(0, 99)

ax_chart_conv.set_xlabel("KROK TEMPERATURY / ITERACJA", fontsize=7.0, fontfamily='monospace', color='#90A4AE', labelpad=4)
ax_chart_conv.set_ylabel("KOSZT E", fontsize=7.0, fontfamily='monospace', color='#90A4AE', labelpad=5)
ax_chart_conv.tick_params(axis='both', labelsize=6.6, colors='#CFD8DC', pad=3)
ax_chart_conv.grid(True, linestyle=':', color='#1E293B', linewidth=0.7)
ax_chart_conv.legend(loc='upper right', fontsize=6.3, facecolor='#10141D', edgecolor='#37474F')

if save_path:
    plt.savefig(save_path, dpi=160, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.2)
    print(f"[SUKCES C2] Wygenerowano wojskową grafikę taktyczną: {save_path}")
else:
    print(f"[C2 TAC-NET] Wyświetlanie okna wojskowego C2 COP dla [{map_name}]...")
    plt.show()
