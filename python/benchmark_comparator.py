#!/usr/bin/env python3
"""
UAV Tactical Routing - Multi-Algorithm Benchmark & Metrics Comparator
Porównuje:
1. Brak wyznaczania trasy (Prosta bazowa)
2. Local Search (Tylko lokalna optymalizacja)
3. Czyste Simulated Annealing (Przed wygładzeniem)
4. SA + Local Search (Zintegrowana hybryda)

Generuje:
- Podsumowanie tabelaryczne metryk (Koszt E, Dystans, Zagrożenie OPL, Krętość, Czas lotu)
- Wykresy słupkowe kosztu, zagrożenia i długości trasy
- Zestawienie skuteczności optymalizacji (%)
"""

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

SCENARIOS = {
    "test_1_flat": "data/maps/test_1_flat.json",
    "test_2_ridge_wall": "data/maps/test_2_ridge_wall.json",
    "test_3_canyon_peaks": "data/maps/test_3_canyon_peaks.json",
    "perlin_full": "data/maps/perlin_full_test_map.json",
}

def load_data(filepath):
    if not os.path.exists(filepath):
        alt = os.path.join("..", filepath)
        if os.path.exists(alt):
            filepath = alt
        else:
            return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def run_benchmark(save_path=None):
    results = {}

    for key, path in SCENARIOS.items():
        d = load_data(path)
        if not d:
            continue
        comp = d.get("comparison", {})
        if not comp:
            continue
        results[key] = comp

    if not results:
        print("[BŁĄD] Brak danych porównawczych w plikach JSON. Uruchom najpierw: ./build/UAVPlanner")
        return

    print("==========================================================================================")
    print("           UAV TACTICAL ROUTING: WIELOKRYTERIALNE ZESTAWIENIE BENCHMARKOWE                ")
    print("==========================================================================================")

    for sc_name, comp in results.items():
        print(f"\n>>> SCENARIUSZ: [{sc_name.upper()}] <<<")
        print(f"{'Algorytm':<25} | {'Koszt E':<10} | {'Dystans (m)':<12} | {'OPL R_eff':<10} | {'Krętość':<8} | {'ETA (s)':<8}")
        print("-" * 84)
        for alg_key in ["baseline", "pure_ls", "pure_sa", "sa_ls"]:
            if alg_key in comp:
                r = comp[alg_key]
                print(f"{r.get('name', alg_key):<25} | "
                      f"{r.get('totalCost', 0.0):<10.1f} | "
                      f"{r.get('distance', 0.0):<12.1f} | "
                      f"{r.get('threatRisk', 0.0):<10.2f} | "
                      f"{r.get('tortuosity', 1.0):<8.2f} | "
                      f"{r.get('flightTimeSec', 0.0):<8.1f}")

    # Plot multi-scenario benchmark figure
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(18, 11), facecolor='#0B0E14')
    fig.canvas.manager.set_window_title("UAV TACTICAL ROUTING - ALGORITHM COMPARATIVE BENCHMARK")

    scenario_labels = [k.replace("_", " ").title() for k in results.keys()]
    x = np.arange(len(scenario_labels))
    width = 0.18

    # Chart 1: Total Cost E across scenarios
    ax1 = axes[0, 0]
    ax1.set_facecolor('#10141D')
    ax1.set_title("1. ŁĄCZNY KOSZT TRASY E(PATH) [IM MNIEJSZY TYM LEPSZY]", fontsize=9.5, fontweight='bold', color='#00E5FF')
    colors = {'baseline': '#FF1744', 'pure_ls': '#FF9100', 'pure_sa': '#E040FB', 'sa_ls': '#00E5FF'}
    labels = {'baseline': 'Prosta (Brak)', 'pure_ls': 'Local Search', 'pure_sa': 'Czyste SA', 'sa_ls': 'SA + Local Search'}

    for idx, alg_key in enumerate(['baseline', 'pure_ls', 'pure_sa', 'sa_ls']):
        vals = [results[sc][alg_key].get('totalCost', 0.0) for sc in results]
        bars = ax1.bar(x + (idx - 1.5) * width, vals, width, label=labels[alg_key], color=colors[alg_key], alpha=0.88, edgecolor='#FFFFFF', linewidth=0.5)
        for b in bars:
            h = b.get_height()
            if h > 0:
                ax1.text(b.get_x() + b.get_width()/2., h + 20, f"{h:.0f}", ha='center', va='bottom', fontsize=6.5, color='#FFFFFF', rotation=45)

    ax1.set_xticks(x)
    ax1.set_xticklabels(scenario_labels, fontsize=8, color='#CFD8DC')
    ax1.set_ylabel("KOSZT E", fontsize=8, color='#90A4AE')
    ax1.legend(loc='upper right', fontsize=7.5, facecolor='#0E121A')
    ax1.grid(True, linestyle=':', color='#1E293B', linewidth=0.7, axis='y')

    # Chart 2: Threat Exposure R_eff across scenarios
    ax2 = axes[0, 1]
    ax2.set_facecolor('#10141D')
    ax2.set_title("2. EKSPOZYCJA NA ZAGROŻENIE OPL (R_EFF) [MINIMALIZACJA RYZYKA]", fontsize=9.5, fontweight='bold', color='#00E5FF')

    for idx, alg_key in enumerate(['baseline', 'pure_ls', 'pure_sa', 'sa_ls']):
        vals = [results[sc][alg_key].get('threatRisk', 0.0) for sc in results]
        ax2.bar(x + (idx - 1.5) * width, vals, width, label=labels[alg_key], color=colors[alg_key], alpha=0.88, edgecolor='#FFFFFF', linewidth=0.5)

    ax2.set_xticks(x)
    ax2.set_xticklabels(scenario_labels, fontsize=8, color='#CFD8DC')
    ax2.set_ylabel("ZAGROŻENIE OPL", fontsize=8, color='#90A4AE')
    ax2.legend(loc='upper right', fontsize=7.5, facecolor='#0E121A')
    ax2.grid(True, linestyle=':', color='#1E293B', linewidth=0.7, axis='y')

    # Chart 3: Distance and Tortuosity
    ax3 = axes[1, 0]
    ax3.set_facecolor('#10141D')
    ax3.set_title("3. DŁUGOŚĆ TRASY 3D (L_3D w metrach) [WPŁYW OMIJANIA]", fontsize=9.5, fontweight='bold', color='#00E5FF')

    for idx, alg_key in enumerate(['baseline', 'pure_ls', 'pure_sa', 'sa_ls']):
        vals = [results[sc][alg_key].get('distance', 0.0) for sc in results]
        ax3.bar(x + (idx - 1.5) * width, vals, width, label=labels[alg_key], color=colors[alg_key], alpha=0.88, edgecolor='#FFFFFF', linewidth=0.5)

    ax3.set_xticks(x)
    ax3.set_xticklabels(scenario_labels, fontsize=8, color='#CFD8DC')
    ax3.set_ylabel("DYSTANS (m)", fontsize=8, color='#90A4AE')
    ax3.legend(loc='upper left', fontsize=7.5, facecolor='#0E121A')
    ax3.grid(True, linestyle=':', color='#1E293B', linewidth=0.7, axis='y')

    # Chart 4: % Improvement vs Baseline
    ax4 = axes[1, 1]
    ax4.set_facecolor('#10141D')
    ax4.set_title("4. SKUTECZNOŚĆ OPTYMALIZACJI (% REDUKCJI KOSZTU vs PROSTA)", fontsize=9.5, fontweight='bold', color='#00E5FF')

    comp_algs = ['pure_ls', 'pure_sa', 'sa_ls']
    width_imp = 0.24
    x_imp = np.arange(len(scenario_labels))

    for idx, alg_key in enumerate(comp_algs):
        imp_vals = []
        for sc in results:
            b_cost = results[sc]['baseline'].get('totalCost', 1.0)
            a_cost = results[sc][alg_key].get('totalCost', 1.0)
            imp = ((b_cost - a_cost) / b_cost * 100.0) if b_cost > 0.001 else 0.0
            imp_vals.append(max(0.0, imp))
        bars = ax4.bar(x_imp + (idx - 1) * width_imp, imp_vals, width_imp, label=labels[alg_key], color=colors[alg_key], alpha=0.88, edgecolor='#FFFFFF', linewidth=0.5)
        for b in bars:
            h = b.get_height()
            ax4.text(b.get_x() + b.get_width()/2., h + 1.5, f"{h:.1f}%", ha='center', va='bottom', fontsize=7.0, color='#FFFFFF')

    ax4.set_xticks(x_imp)
    ax4.set_xticklabels(scenario_labels, fontsize=8, color='#CFD8DC')
    ax4.set_ylabel("ZYSK PROCENTOWY (%)", fontsize=8, color='#90A4AE')
    ax4.set_ylim(0, 105)
    ax4.legend(loc='upper left', fontsize=7.5, facecolor='#0E121A')
    ax4.grid(True, linestyle=':', color='#1E293B', linewidth=0.7, axis='y')

    plt.tight_layout()

    out_file = save_path if save_path else "benchmark_summary.png"
    plt.savefig(out_file, dpi=160, facecolor=fig.get_facecolor(), bbox_inches='tight')
    print(f"\n[SUKCES] Zapisano zestawienie porównawcze do: {out_file}")

    if not save_path and "Agg" not in matplotlib.get_backend():
        plt.show()

if __name__ == "__main__":
    out_arg = None
    for i, a in enumerate(sys.argv):
        if a in ["--save", "-s"] and i + 1 < len(sys.argv):
            out_arg = sys.argv[i + 1]
    run_benchmark(out_arg)
