#include <iostream>
#include <iomanip>
#include <random>
#include <cassert>
#include "map/Map.h"
#include "map/generators/MapGenerator.h"
#include "map/generators/TestMapGenerator.h"
#include "map/threats/ThreatMap.h"
#include "routing/Waypoint.h"
#include "routing/Path.h"
#include "routing/Mission.h"
#include "planner/CostEvaluator.h"
#include "planner/LocalSearch.h"
#include "planner/SimulatedAnnealing.h"
#include "io/JsonExporter.h"
#include "io/JsonMapImporter.h"
#include "io/ScenarioRunner.h"

void printCostComparison(const std::string& scenarioName,
                         const CostBreakdown& before,
                         const CostBreakdown& after,
                         const SAResult& saResult) {
    float improvement = 0.0f;
    float baseCost = saResult.baseline.cost.totalCost;
    if (baseCost > 0.001f) {
        improvement = (baseCost - saResult.hybridSaLs.cost.totalCost) / baseCost * 100.0f;
    }

    std::cout << "\n==========================================================================================" << std::endl;
    std::cout << "  OPTYMALIZACJA TRASY UAV: " << scenarioName << std::endl;
    std::cout << "==========================================================================================" << std::endl;
    std::cout << std::fixed << std::setprecision(2);

    std::cout << "  PORÓWNANIE ALGORYTMÓW (Brak planowania vs Local Search vs SA vs SA+LS):" << std::endl;
    std::cout << "  ----------------------------------------------------------------------------------------" << std::endl;
    std::cout << "  Metryka                | 1. Baza (Prosta) | 2. Local Search  | 3. Czyste SA     | 4. SA+Local (Optimum)" << std::endl;
    std::cout << "  -----------------------+------------------+------------------+------------------+----------------------" << std::endl;

    std::cout << "  Łączny koszt E(Path)   | "
              << std::setw(16) << saResult.baseline.cost.totalCost << " | "
              << std::setw(16) << saResult.pureLocalSearch.cost.totalCost << " | "
              << std::setw(16) << saResult.pureSA.cost.totalCost << " | "
              << std::setw(16) << saResult.hybridSaLs.cost.totalCost << std::endl;

    std::cout << "  Długość 3D L_3D (m)    | "
              << std::setw(16) << saResult.baseline.cost.distance << " | "
              << std::setw(16) << saResult.pureLocalSearch.cost.distance << " | "
              << std::setw(16) << saResult.pureSA.cost.distance << " | "
              << std::setw(16) << saResult.hybridSaLs.cost.distance << std::endl;

    std::cout << "  Zagrożenie OPL R_eff   | "
              << std::setw(16) << saResult.baseline.cost.threatRisk << " | "
              << std::setw(16) << saResult.pureLocalSearch.cost.threatRisk << " | "
              << std::setw(16) << saResult.pureSA.cost.threatRisk << " | "
              << std::setw(16) << saResult.hybridSaLs.cost.threatRisk << std::endl;

    std::cout << "  Punkty trasy (WP)      | "
              << std::setw(16) << saResult.baseline.waypointsCount << " | "
              << std::setw(16) << saResult.pureLocalSearch.waypointsCount << " | "
              << std::setw(16) << saResult.pureSA.waypointsCount << " | "
              << std::setw(16) << saResult.hybridSaLs.waypointsCount << std::endl;

    std::cout << "  Krętość (Tortuosity)   | "
              << std::setw(16) << saResult.baseline.tortuosity << " | "
              << std::setw(16) << saResult.pureLocalSearch.tortuosity << " | "
              << std::setw(16) << saResult.pureSA.tortuosity << " | "
              << std::setw(16) << saResult.hybridSaLs.tortuosity << std::endl;

    std::cout << "  Czas lotu (60 km/h)    | "
              << std::setw(14) << saResult.baseline.flightTimeSec << "s | "
              << std::setw(14) << saResult.pureLocalSearch.flightTimeSec << "s | "
              << std::setw(14) << saResult.pureSA.flightTimeSec << "s | "
              << std::setw(14) << saResult.hybridSaLs.flightTimeSec << "s" << std::endl;

    std::cout << "  Status wykonalności    | "
              << std::setw(16) << (saResult.baseline.cost.isFeasible ? "WYKONALNA" : "KOLIZJE") << " | "
              << std::setw(16) << (saResult.pureLocalSearch.cost.isFeasible ? "WYKONALNA" : "KOLIZJE") << " | "
              << std::setw(16) << (saResult.pureSA.cost.isFeasible ? "WYKONALNA" : "KOLIZJE") << " | "
              << std::setw(16) << (saResult.hybridSaLs.cost.isFeasible ? "WYKONALNA" : "KOLIZJE") << std::endl;

    std::cout << "  ----------------------------------------------------------------------------------------" << std::endl;
    std::cout << "  Skuteczność optymalizacji:" << std::endl;
    std::cout << "     -> Redukcja funkcji celu: " << (baseCost - saResult.hybridSaLs.cost.totalCost)
              << " pkt (" << improvement << "% zysku względem prostej!)" << std::endl;
    std::cout << "     -> Statystyki SA: " << saResult.totalIterations << " prób, "
              << saResult.acceptedBetterMoves << " lepszych, " << saResult.acceptedWorseMoves << " przeskoków (Metropolis)" << std::endl;

    if (!saResult.decisionLog.empty()) {
        std::cout << "  Kronika kluczowych decyzji algorytmu (" << saResult.decisionLog.size() << " zarejestrowanych zdarzeń):" << std::endl;
        size_t showCount = std::min<size_t>(saResult.decisionLog.size(), 6);
        for (size_t i = 0; i < showCount; ++i) {
            const auto& ev = saResult.decisionLog[i];
            std::cout << "     [" << ev.phase << " | Krok " << std::setw(3) << ev.iteration
                      << " | T=" << std::setw(5) << std::setprecision(1) << ev.temperature << "] "
                      << ev.details << std::endl;
        }
        if (saResult.decisionLog.size() > showCount) {
            std::cout << "     ... i jeszcze " << (saResult.decisionLog.size() - showCount) << " dalszych decyzji zapisanych w JSON." << std::endl;
        }
    }
}

void generatePerlinMap() {
    std::cout << "\n=== [MAPA GŁÓWNA] Proceduralny Teren Perlin (100x100) ===" << std::endl;
    int seed = 12312;
    std::mt19937 rng(seed);

    Map map(100, 100);
    MapGenerator::generateProceduralMap(map, seed);

    ThreatMap threatMap;
    threatMap.generateProceduralRadars(map, 2, 30.0f, rng);
    threatMap.calculateThreats(map, 10.0f);

    Waypoint start(1, 5.0f, 5.0f, 10.0f, WaypointType::Start, "Baza Startowa Alpha");
    Waypoint wp1(2, 15.0f, 80.0f, 10.0f, WaypointType::Reconnaissance, "Cel 1 (Północ)");
    Waypoint wp2(3, 85.0f, 10.0f, 10.0f, WaypointType::Reconnaissance, "Cel 2 (Wschód)");
    Waypoint returnBase(4, 90.0f, 90.0f, 10.0f, WaypointType::Return, "Lądowisko Bravo");

    Mission mission(start, returnBase);
    mission.addTarget(wp1);
    mission.addTarget(wp2);

    CostEvaluator evaluator(1.0f, 60.0f, 10000.0f);
    SAParameters params;
    params.initialTemperature = 600.0f;
    params.minTemperature = 0.05f;
    params.coolingRate = 0.992f;
    params.iterationsPerTemp = 20;
    params.maxPerturbation = 10.0f;

    SimulatedAnnealing sa(evaluator, params);
    SAResult saResult = sa.optimize(mission, map, 12345);

    printCostComparison("Perlin Main Map (Proceduralna Fuzja Terenu i OPL)",
                        saResult.initialCost, saResult.bestCost, saResult);

    JsonExporter::save(map, "data/maps/perlin_full_test_map.json", threatMap.getRadars(),
                      &mission, &saResult.bestPath, &saResult.bestWaypoints, &saResult.decisionLog, &saResult);
    std::cout << "-> Zapisano zoptymalizowaną trasę i kronikę decyzji: data/maps/perlin_full_test_map.json" << std::endl;
}

void generateTestMap1_Flat() {
    std::cout << "\n=== [TEST 1] Płaski Teren - Weryfikacja kołowego omijania radaru ===" << std::endl;
    Map map(80, 80);
    TestMapGenerator::generateFlatMap(map, 5.0f);

    ThreatMap threatMap;
    threatMap.addRadar(RadarStation(1, 40, 40, 28.0f, 1.0f, 15.0f));
    threatMap.calculateThreats(map, 10.0f);

    Waypoint start(1, 5.0f, 40.0f, 10.0f, WaypointType::Start, "Start Zachód");
    Waypoint wp1(2, 75.0f, 40.0f, 10.0f, WaypointType::Reconnaissance, "Cel Wschód");
    Waypoint returnBase(3, 5.0f, 70.0f, 10.0f, WaypointType::Return, "Baza Południe");

    Mission mission(start, returnBase);
    mission.addTarget(wp1);

    CostEvaluator evaluator(1.0f, 80.0f, 10000.0f);
    SAParameters params;
    params.initialTemperature = 800.0f;
    params.minTemperature = 0.05f;
    params.coolingRate = 0.993f;
    params.iterationsPerTemp = 25;
    params.maxPerturbation = 12.0f;

    SimulatedAnnealing sa(evaluator, params);
    SAResult saResult = sa.optimize(mission, map, 42);

    printCostComparison("Test 1 Flat (Omijanie strefy radaru po obwodzie)",
                        saResult.initialCost, saResult.bestCost, saResult);

    JsonExporter::save(map, "data/maps/test_1_flat.json", threatMap.getRadars(),
                      &mission, &saResult.bestPath, &saResult.bestWaypoints, &saResult.decisionLog, &saResult);
    std::cout << "-> Zapisano zoptymalizowaną trasę i kronikę decyzji: data/maps/test_1_flat.json" << std::endl;
}

void generateTestMap2_RidgeWall() {
    std::cout << "\n=== [TEST 2] Grzbiet Górski - Weryfikacja cienia radarowego (Radar Shadow) ===" << std::endl;
    Map map(80, 80);
    TestMapGenerator::generateRidgeMap(map, 5.0f, 45.0f);

    ThreatMap threatMap;
    threatMap.addRadar(RadarStation(1, 20, 40, 35.0f, 1.0f, 15.0f));
    threatMap.calculateThreats(map, 10.0f);

    Waypoint start(1, 10.0f, 20.0f, 10.0f, WaypointType::Start, "Baza Zachód");
    Waypoint target(2, 70.0f, 40.0f, 10.0f, WaypointType::Reconnaissance, "Cel za Grzbietem");
    Waypoint returnBase(3, 10.0f, 60.0f, 10.0f, WaypointType::Return, "Powrót");

    Mission mission(start, returnBase);
    mission.addTarget(target);

    CostEvaluator evaluator(1.0f, 60.0f, 10000.0f);
    SAParameters params;
    params.initialTemperature = 700.0f;
    params.coolingRate = 0.993f;
    params.iterationsPerTemp = 20;

    SimulatedAnnealing sa(evaluator, params);
    SAResult saResult = sa.optimize(mission, map, 777);

    printCostComparison("Test 2 Ridge Wall (Wykorzystanie cienia grzbietu)",
                        saResult.initialCost, saResult.bestCost, saResult);

    JsonExporter::save(map, "data/maps/test_2_ridge_wall.json", threatMap.getRadars(),
                      &mission, &saResult.bestPath, &saResult.bestWaypoints, &saResult.decisionLog, &saResult);
    std::cout << "-> Zapisano zoptymalizowaną trasę i kronikę decyzji: data/maps/test_2_ridge_wall.json" << std::endl;
}

void generateTestMap3_CanyonPeaks() {
    std::cout << "\n=== [TEST 3] Szczyty vs Kanion - Weryfikacja korytarza w dolinie ===" << std::endl;
    Map map(80, 80);
    TestMapGenerator::generateCanyonMap(map, 25.0f, 35.0f, 23.0f);

    ThreatMap threatMap;
    threatMap.addRadar(RadarStation(1, 20, 40, 30.0f, 1.0f, 15.0f));
    threatMap.addRadar(RadarStation(2, 40, 40, 30.0f, 1.0f, 15.0f));
    threatMap.calculateThreats(map, 10.0f);

    Waypoint start(1, 10.0f, 10.0f, 10.0f, WaypointType::Start, "Baza Północ");
    Waypoint target(2, 40.0f, 70.0f, 10.0f, WaypointType::Reconnaissance, "Cel w Kanionie");
    Waypoint returnBase(3, 70.0f, 10.0f, 10.0f, WaypointType::Return, "Lądowisko Wschód");

    Mission mission(start, returnBase);
    mission.addTarget(target);

    CostEvaluator evaluator(1.0f, 70.0f, 10000.0f);
    SAParameters params;
    params.initialTemperature = 700.0f;
    params.coolingRate = 0.993f;
    params.iterationsPerTemp = 20;

    SimulatedAnnealing sa(evaluator, params);
    SAResult saResult = sa.optimize(mission, map, 888);

    printCostComparison("Test 3 Canyon (Nawigacja dnem kanionu)",
                        saResult.initialCost, saResult.bestCost, saResult);

    JsonExporter::save(map, "data/maps/test_3_canyon_peaks.json", threatMap.getRadars(),
                      &mission, &saResult.bestPath, &saResult.bestWaypoints, &saResult.decisionLog, &saResult);
    std::cout << "-> Zapisano zoptymalizowaną trasę i kronikę decyzji: data/maps/test_3_canyon_peaks.json" << std::endl;
}

void demonstrateStep4HybridOptimizerSuite() {
    std::cout << "\n=======================================================" << std::endl;
    std::cout << "  KROK 4: TESTY JEDNOSTKOWE SA + LOCAL SEARCH          " << std::endl;
    std::cout << "=======================================================" << std::endl;

    Map testMap(40, 40);
    TestMapGenerator::generateFlatMap(testMap, 0.0f);

    ThreatMap threatMap;
    threatMap.addRadar(RadarStation(1, 20, 20, 15.0f, 1.0f, 10.0f));
    threatMap.calculateThreats(testMap, 10.0f);

    Waypoint start(1, 5.0f, 20.0f, 10.0f, WaypointType::Start, "Start");
    Waypoint goal(2, 35.0f, 20.0f, 10.0f, WaypointType::Return, "Goal");
    Mission mission(start, goal);

    CostEvaluator evaluator(1.0f, 100.0f, 10000.0f);
    SimulatedAnnealing sa(evaluator);

    std::cout << "\n[TEST 4.1] Globalna optymalizacja Simulated Annealing:" << std::endl;
    SAResult result = sa.optimize(mission, testMap, 999);
    std::cout << "  - Koszt początkowy (przelot przez środek radaru): " << result.initialCost.totalCost << std::endl;
    std::cout << "  - Koszt zoptymalizowany (omijanie radaru):       " << result.bestCost.totalCost << std::endl;
    std::cout << "  - Liczba wykonanych prób:                        " << result.totalIterations << std::endl;
    std::cout << "  - Zaakceptowane ruchy poprawiające:              " << result.acceptedBetterMoves << std::endl;
    std::cout << "  - Zaakceptowane przeskoki gorsze (Metropolis):   " << result.acceptedWorseMoves << std::endl;

    assert(result.bestCost.totalCost < result.initialCost.totalCost);
    assert(result.bestCost.isFeasible);

    std::cout << "\n[TEST 4.2] Local Search (Wygładzanie i Shortcutting):" << std::endl;

    std::vector<Waypoint> zigzagWaypoints;
    zigzagWaypoints.emplace_back(1, 2.0f, 2.0f, 10.0f, WaypointType::Start, "Start");
    zigzagWaypoints.emplace_back(2, 5.0f, 3.0f, 10.0f, WaypointType::Transit, "Z1");
    zigzagWaypoints.emplace_back(3, 4.0f, 2.0f, 10.0f, WaypointType::Transit, "Z2");
    zigzagWaypoints.emplace_back(4, 7.0f, 3.0f, 10.0f, WaypointType::Transit, "Z3");
    zigzagWaypoints.emplace_back(5, 10.0f, 2.0f, 10.0f, WaypointType::Return, "Return");

    Path zigPath = LocalSearch::buildDensePath(zigzagWaypoints, testMap);
    CostBreakdown zigCost = evaluator.evaluate(zigPath, testMap);

    std::vector<Waypoint> smoothed = LocalSearch::optimize(zigzagWaypoints, testMap, evaluator);
    Path smoothPath = LocalSearch::buildDensePath(smoothed, testMap);
    CostBreakdown smoothCost = evaluator.evaluate(smoothPath, testMap);

    std::cout << "  - Liczba punktów przed Local Search: " << zigzagWaypoints.size()
              << " (Dystans: " << zigCost.distance << "m, Koszt: " << zigCost.totalCost << ")" << std::endl;
    std::cout << "  - Liczba punktów po Local Search:    " << smoothed.size()
              << " (Dystans: " << smoothCost.distance << "m, Koszt: " << smoothCost.totalCost << ")" << std::endl;

    assert(smoothCost.totalCost <= zigCost.totalCost);
    assert(smoothed.size() <= zigzagWaypoints.size());

    std::cout << "\n[SUKCES KROK 4] Wszystkie asercje i testy SA + Local Search zakończone pomyślnie!" << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc > 1) {
        if (std::string(argv[1]) == "--help") {
            std::cout << "Usage: UAVPlanner [--map imported.json --output exported.json]\n"
                         "       UAVPlanner --scenario scenario.json --output result.json\n"
                         "Without arguments: existing Perlin and test scenarios.\n"
                         "--map: load and export an OSM+NMT terrain for inspection.\n";
            return 0;
        }
        if (argc != 5 || (std::string(argv[1]) != "--map" && std::string(argv[1]) != "--scenario") || std::string(argv[3]) != "--output") {
            std::cerr << "Usage: UAVPlanner --map|--scenario input.json --output output.json\n";
            return 1;
        }
        try {
            if (std::string(argv[1]) == "--scenario") {
                runScenario(argv[2], argv[4]);
                return 0;
            }
            Map map = JsonMapImporter::load(argv[2]);
            JsonExporter::save(map, argv[4]);
            std::cout << "Loaded OSM+NMT map: " << map.getWidth() << " x "
                      << map.getHeight() << " m. Exported to " << argv[4] << '\n';
            return 0;
        } catch (const std::exception& error) {
            std::cerr << "Map import failed: " << error.what() << '\n';
            return 1;
        }
    }
    std::cout << "=======================================================" << std::endl;
    std::cout << "  PLANOWANIE TRAS UAV - SIMULATED ANNEALING & LOCAL SEARCH " << std::endl;
    std::cout << "=======================================================" << std::endl;

    generatePerlinMap();
    generateTestMap1_Flat();
    generateTestMap2_RidgeWall();
    generateTestMap3_CanyonPeaks();
    demonstrateStep4HybridOptimizerSuite();

    std::cout << "\n[SUKCES] Wszystkie optymalizacje tras i testy wykonano pomyślnie!" << std::endl;
    return 0;
}
