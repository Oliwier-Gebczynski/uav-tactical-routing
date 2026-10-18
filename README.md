# UAV Tactical 3D Trajectory Planner & C2 Battlefield Visualizer

An end-to-end tactical mission routing system for Unmanned Aerial Vehicles (UAVs) operating in hostile, radar-contested 3D environments. The system couples a procedural terrain engine (Digital Elevation Models, biomes, radar shadows) with a **Hybrid Optimizer (Simulated Annealing + Local Search)** and an integrated **Military C2 (Command & Control) Analytical Dashboard**.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Project Architecture](#project-architecture)
3. [Prerequisites & Installation](#prerequisites--installation)
4. [Building and Running the C++ Planner](#building-and-running-the-c-planner)
5. [How to Generate New Maps & Change Seeds](#how-to-generate-new-maps--change-seeds)
6. [Visualization Tools & Viewer Versions](#visualization-tools--viewer-versions)
   - [Viewer 1: Tactical C2 COP & Algorithm Benchmark (`dashboard`)](#viewer-1-tactical-c2-cop--algorithm-benchmark-dashboard)
   - [Viewer 2: Cross-Scenario Benchmark Comparator (`benchmark`)](#viewer-2-cross-scenario-benchmark-comparator-benchmark)
   - [Viewer 3: 4-Quadrant Terrain & Threat Analyzer (`view`)](#viewer-3-4-quadrant-terrain--threat-analyzer-view)
7. [Algorithm Comparison & Evaluated Metrics](#algorithm-comparison--evaluated-metrics)
8. [Multi-Objective Objective Function](#multi-objective-objective-function)

---

## Key Features

The desktop [UAV Mission Control](docs/mission-control.md) application provides
OSM+NMT map generation, a clickable radar and waypoint editor, portable scenario
files and simulation result panels. Launch with:

```bash
python/venv/bin/python python/main.py gui
```

* **3D Terrain & Radar Shadow Modeling**: Computes Line-of-Sight (LOS) radar coverage taking into account Digital Elevation Models (DEM), creating realistic radar shadows behind ridges, valleys, and canyons.
* **Biome Concealment**: Rewards low-altitude masking over forests and valleys to reduce detection probability ($R_{\text{eff}} = R_{\text{raw}} \cdot (1 - \text{concealment})$).
* **Hybrid Optimization Engine**:
  * **Simulated Annealing (SA)**: Global non-convex optimization with Metropolis acceptance criteria to escape local minima, utilizing dynamic waypoint insertion, Gaussian perturbation, and waypoint pruning.
  * **Local Search (LS)**: Multi-pass gradient descent, obstacle-free shortcutting, and collinear segment smoothing.
* **4-Algorithm Benchmark Suite**: Simultaneously computes and compares:
  1. **Direct Baseline (Straight line)**: No tactical planning (flies straight through air defense zones).
  2. **Pure Local Search**: Local descent from the baseline (demonstrates trapping in local minima).
  3. **Pure Simulated Annealing**: Global avoidance prior to trajectory smoothing.
  4. **SA + Local Search (Hybrid Optimum)**: Globally safe, smoothed, Pareto-efficient trajectory.

---

## Project Architecture

```
uav-tactical-routing/
├── CMakeLists.txt              # CMake build configuration (C++20)
├── build/                      # Compiled binaries and build artifacts
├── data/
│   └── maps/                   # Exported operational JSON mission files
│       ├── test_1_flat.json
│       ├── test_2_ridge_wall.json
│       ├── test_3_canyon_peaks.json
│       └── perlin_full_test_map.json
├── python/
│   ├── main.py                # GUI and command-line entry point
│   ├── uav_routing/
│   │   ├── gui/               # Desktop application
│   │   ├── maps/              # OSM + NMT importer
│   │   ├── scenarios/         # Scenario documents and validation
│   │   ├── visualization/     # Terrain, tactical and benchmark viewers
│   │   └── paths.py           # Shared repository path resolution
│   ├── tests/                 # Unit/integration tests and shared fixtures
│   ├── requirements/          # Base and map-import dependencies
│   └── venv/                  # Preconfigured virtual environment
└── src/
    ├── main.cpp                # Execution entry point & test scenarios
    ├── map/                    # Grid map, biomes, Perlin noise & DEM generators
    ├── threats/                # SAM radar stations & line-of-sight raycasters
    ├── routing/                # Waypoints, 3D paths, and mission definitions
    ├── planner/                # CostEvaluator, SimulatedAnnealing & LocalSearch
    └── io/                     # JsonExporter for visualization exchange
```

---

## Prerequisites & Installation

### 1. C++ Compiler & CMake
* **C++20 compatible compiler**: GCC 11+ or Clang 13+
* **CMake**: Version 3.20 or newer
* **nlohmann-json**: `sudo apt-get install nlohmann-json3-dev` (or detected automatically)

### 2. Python Environment
A virtual environment is pre-configured in `python/venv`. To use the system environment instead:
```bash
python3 -m venv python/venv
source python/venv/bin/activate
pip install -r python/requirements/base.txt
```

---

## Building and Running the C++ Planner

### 1. Build the Executable
From the repository root:
```bash
cmake -B build
cmake --build build
```

### 2. Run the Optimization Suite
```bash
./build/UAVPlanner
```

When executed, the system:
1. Runs the procedural terrain and threat synthesizers for all scenarios.
2. Executes the hybrid SA + Local Search optimization for each map.
3. Prints detailed console benchmark tables comparing the 4 algorithmic approaches.
4. Executes unit tests and verification assertions (Step 4 Hybrid Suite).
5. Exports complete operational data, all paths, convergence history, and decision chronicles to `data/maps/*.json`.

---

## How to Generate New Maps & Change Seeds

Polish OSM + GUGiK NMT maps are also supported. See
[Mapy Polski: OSM + NMT](docs/polskie-mapy.md) for the Gliwice example,
height estimation rules, local/offline import and C++ loading instructions.

All scenario configurations and procedural generation seeds are defined in [`src/main.cpp`](file:///home/opg/Documents/uav-tactical-routing/src/main.cpp).

### Changing the Procedural Map Seed
Open `src/main.cpp` and locate the `generatePerlinMap()` function:

```cpp
void generatePerlinMap() {
    std::cout << "\n=== [MAPA GŁÓWNA] Proceduralny Teren Perlin (100x100) ===" << std::endl;
    
    // 1. CHANGE SEED HERE:
    int seed = 12345; // Put any integer value here
    std::mt19937 rng(seed);

    // 2. Set map dimensions:
    Map map(100, 100);
    MapGenerator::generateProceduralMap(map, seed);

    // 3. Customize number of radar stations and their detection range:
    ThreatMap threatMap;
    threatMap.generateProceduralRadars(map, 4, 32.0f, rng); // (map, count, maxRange, rng)
    threatMap.calculateThreats(map, 10.0f);

    // 4. Customize mission waypoints:
    Waypoint start(1, 5.0f, 5.0f, 10.0f, WaypointType::Start, "Baza Startowa Alpha");
    Waypoint wp1(2, 45.0f, 25.0f, 10.0f, WaypointType::Reconnaissance, "Cel 1");
    Waypoint returnBase(3, 15.0f, 90.0f, 10.0f, WaypointType::Return, "Lądowisko Bravo");

    Mission mission(start, returnBase);
    mission.addTarget(wp1);

    // 5. Tune Simulated Annealing hyperparameters:
    CostEvaluator evaluator(1.0f, 60.0f, 10000.0f); // (distWeight, threatWeight, collisionWeight)
    SAParameters params;
    params.initialTemperature = 700.0f;
    params.coolingRate = 0.993f;
    params.iterationsPerTemp = 25;

    SimulatedAnnealing sa(evaluator, params);
    SAResult saResult = sa.optimize(mission, map, seed);

    // 6. Save results:
    JsonExporter::save(map, "data/maps/perlin_full_test_map.json", threatMap.getRadars(),
                      &mission, &saResult.bestPath, &saResult.bestWaypoints, &saResult.decisionLog, &saResult);
}
```

After modifying the seed or parameters, recompile and re-run:
```bash
cmake --build build && ./build/UAVPlanner
```

---

## Visualization Tools & Viewer Versions

The project includes three distinct Python visualizers suited for different analysis tasks.

### Viewer 1: Tactical C2 COP & Algorithm Benchmark (`dashboard`)
This is the **primary military-grade Command & Control dashboard**. It displays the entire operational picture side-by-side with multi-algorithm comparative analytics.

#### Screen Layout:
* **Left Column (Grid 0–11)**:
  * **Top**: Tactical Legend (Land cover categories + 3 path handles).
  * **Center**: 2D Shaded Relief Map showing DEM contour lines, active SAM stations, theoretical detection radii, lethal kill zones, radar shadows, mission waypoints, and **3 flight trajectories**:
    * **Amber dashed line (`--`)**: Direct Baseline (No route planning).
    * **Purple dotted line (`:`)**: Pure Simulated Annealing (pre-smoothing).
    * **Bright Cyan solid line (`-`)**: SA + Local Search optimum with directional flight vectors.
  * **Bottom**: Elevation cross-section profile comparing terrain DEM vs. UAV flight ceiling ($h_{\text{AGL}}$) with highlighted radar hazard exposure zones.
* **Middle Column (Grid 12–17)**:
  * Tactical C2 HUD with a structured multi-algorithm benchmark table, survival metrics, and planer decision chronicle.
* **Right Column (Grid 19–25)**:
  * **Chart 1**: Bar chart comparing Total Cost $E(\text{Path})$ across all 4 methods with numerical value badges and cost reduction percentage.
  * **Chart 2**: Dual-axis Trade-off chart comparing Threat Risk ($R_{\text{eff}}$) vs 3D Flight Distance ($L_{3D}$) for each algorithm.
  * **Chart 3**: Simulated Annealing Convergence History ($E$ vs temperature iteration) with baseline cost threshold and Local Search drop indicator.

#### How to Launch:
```bash
# Using predefined map shortcuts:
./python/venv/bin/python python/main.py dashboard 1       # Test 1: Flat terrain radar circumnavigation
./python/venv/bin/python python/main.py dashboard 2       # Test 2: Ridge wall radar shadow utilization
./python/venv/bin/python python/main.py dashboard 3       # Test 3: Canyon vs peaks navigation
./python/venv/bin/python python/main.py dashboard perlin  # Procedural Perlin fusion map

# Loading any custom map file:
./python/venv/bin/python python/main.py dashboard data/maps/test_1_flat.json

# Headless / Batch export to PNG without opening window:
./python/venv/bin/python python/main.py dashboard 1 --save output_test1.png
./python/venv/bin/python python/main.py dashboard perlin -s c2_perlin_dashboard.png
```

---

### Viewer 2: Cross-Scenario Benchmark Comparator (`benchmark`)
A dedicated multi-scenario benchmark tool that loads all four maps simultaneously and generates aggregate comparative analytics.

#### Features:
* **Chart 1**: Global Cost Comparison $E(\text{Path})$ across all scenarios.
* **Chart 2**: Radar Threat Exposure ($R_{\text{eff}}$) reduction across all scenarios.
* **Chart 3**: 3D Distance & Detour impact.
* **Chart 4**: Optimization efficiency percentage (% reduction vs. straight baseline).
* **Console Summary**: Formatted tabular breakdown printed to stdout.

#### How to Launch:
```bash
# Interactive window:
./python/venv/bin/python python/main.py benchmark

# Save to PNG file:
./python/venv/bin/python python/main.py benchmark --save benchmark_summary.png
```

---

### Viewer 3: 4-Quadrant Terrain & Threat Analyzer (`view`)
A focused four-quadrant diagnostic tool for inspecting map layers:
1. **Quadrant (0,0)**: Land Cover Classification (Water, Grass, Forest, Road, Building).
2. **Quadrant (0,1)**: DEM Elevation Map with colorbar scale.
3. **Quadrant (1,0)**: Threat level distribution with radar coverage circles.
4. **Quadrant (1,1)**: Tactical fusion overlay with shaded 3D relief and UAV path.

#### How to Launch:
```bash
./python/venv/bin/python python/main.py view 1
./python/venv/bin/python python/main.py view 2
./python/venv/bin/python python/main.py view 3
./python/venv/bin/python python/main.py view perlin
```

---

## Algorithm Comparison & Evaluated Metrics

| Metric | Direct Baseline (No Planning) | Pure Local Search | Pure Simulated Annealing | SA + Local Search (Hybrid Optimum) |
| :--- | :--- | :--- | :--- | :--- |
| **Concept** | Direct Euclidean flight from Start to Goal. | Gradient-like steps on baseline transit points. | Global non-convex exploration via SA. | SA exploration + Local Search shortcutting/smoothing. |
| **Total Cost $E$** | Very High (direct hit into radar). | High (trapped in local minimum). | Low (avoids radar, rough path). | **Lowest (Pareto optimal)**. |
| **Radar Threat $R_{\text{eff}}$** | Lethal exposure. | Lethal exposure. | Minimal exposure ($\approx 0$). | **Minimal exposure ($\approx 0$)**. |
| **3D Distance $L_{3D}$** | Shortest (0% detour). | Shortest (cannot detour). | Longer (+20–30% detour). | **Optimized (+18–25% detour)**. |
| **Tortuosity ($L/D$)** | $1.00$ (straight line). | $1.00$–$1.10$. | $1.35$–$1.50$ (jagged). | **$1.15$–$1.25$ (streamlined)**. |
| **Waypoints Count** | 2–3 key targets. | 2–5 points. | 14–20 points. | **8–11 points (pruned & smoothed)**. |
| **Flight Time (ETA)** | Minimum time, zero survival. | Trapped in threat. | Safe, slightly higher ETA. | **Optimal safety-to-time ratio**. |

---

## Multi-Objective Objective Function

The optimizer evaluates candidate trajectories using the multi-criteria cost model implemented in [`src/planner/CostEvaluator.cpp`]:

$$E(\text{Path}) = w_1 \cdot L_{3D} + w_2 \cdot R_{\text{eff}} + w_3 \cdot P_{\text{coll}}$$

Where:
* **$L_{3D}$**: Sum of 3D Euclidean step lengths along the interpolated flight path:
  $$L_{3D} = \sum_{i=1}^{N} \sqrt{(x_i - x_{i-1})^2 + (y_i - y_{i-1})^2 + (z_i - z_{i-1})^2}$$
* **$R_{\text{eff}}$**: Integrated radar exposure accounting for terrain line-of-sight and forest concealment:
  $$R_{\text{eff}} = \sum_{i=1}^{N} \text{threatLevel}(x_i, y_i) \cdot (1 - \text{concealment}(x_i, y_i))$$
* **$P_{\text{coll}}$**: Collision penalty enforcing physical feasibility:
  $$P_{\text{coll}} = \sum_{i=1}^{N} \Big( \mathbb{I}(z_i \le \text{elev}_i) \cdot P_{\text{terrain}} + \mathbb{I}(\text{building}_i) \cdot P_{\text{urban}} + \mathbb{I}(\text{outOfBounds}_i) \cdot P_{\text{bound}} \Big)$$
* Default weight coefficients: $w_1 = 1.0$, $w_2 = 60.0$, $w_3 = 10000.0$.
