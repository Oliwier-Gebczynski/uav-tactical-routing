#include <iostream>
#include <iomanip>
#include <random>
#include "map/Map.h"
#include "map/generators/MapGenerator.h"
#include "map/generators/TestMapGenerator.h"
#include "map/threats/ThreatMap.h"
#include "routing/Waypoint.h"
#include "routing/Path.h"
#include "routing/Mission.h"
#include "io/JsonExporter.h"

void generatePerlinMap() {
    std::cout << "\n=== [MAPA GŁÓWNA] Proceduralny Teren Perlin (100x100) ===" << std::endl;
    int seed = 67;
    std::mt19937 rng(seed);

    Map map(100, 100);
    MapGenerator::generateProceduralMap(map, seed);

    ThreatMap threatMap;
    threatMap.generateProceduralRadars(map, 3, 30.0f, rng);
    threatMap.calculateThreats(map, 10.0f);

    // Krok 2: Definiowanie Misji UAV i Punktów Kontrolnych
    Waypoint start(1, 5.0f, 5.0f, 10.0f, WaypointType::Start, "Baza Startowa Alpha");
    Waypoint wp1(2, 45.0f, 25.0f, 10.0f, WaypointType::Reconnaissance, "Cel 1 (Obiekt Północny)");
    Waypoint wp2(3, 85.0f, 65.0f, 10.0f, WaypointType::Reconnaissance, "Cel 2 (Obiekt Wschodni)");
    Waypoint returnBase(4, 15.0f, 90.0f, 10.0f, WaypointType::Return, "Lądowisko Bravo");

    Mission mission(start, returnBase);
    mission.addTarget(wp1);
    mission.addTarget(wp2);

    Path directPath = mission.generateDirectPath(map);
    auto stats = directPath.getStats(map);

    std::cout << "-> Wygenerowano wstępną trasę misji:" << std::endl;
    std::cout << "   - Liczba punktów kontrolnych: " << mission.getAllWaypoints().size() << std::endl;
    std::cout << "   - Liczba odwiedzonych komórek siatki: " << stats.totalVisitedCells << std::endl;
    std::cout << "   - Całkowity dystans lotu: " << std::fixed << std::setprecision(1) << stats.totalDistance << " m" << std::endl;
    std::cout << "   - Łączna ekspozycja na radar: " << stats.totalThreatExposure << std::endl;
    std::cout << "   - Maksymalne zagrożenie na trasie: " << (stats.maxThreatLevel * 100.0f) << "%" << std::endl;

    JsonExporter::save(map, "data/maps/perlin_full_test_map.json", threatMap.getRadars(), &mission, &directPath);
    std::cout << "-> Zapisano: data/maps/perlin_full_test_map.json" << std::endl;
}

void generateTestMap1_Flat() {
    std::cout << "\n=== [TEST 1] Płaski Teren - Weryfikacja kołowego zasięgu radaru ===" << std::endl;
    Map map(80, 80);
    TestMapGenerator::generateFlatMap(map, 5.0f);

    ThreatMap threatMap;
    threatMap.addRadar(RadarStation(1, 40, 40, 28.0f, 1.0f, 15.0f));
    threatMap.calculateThreats(map, 10.0f);

    Waypoint start(1, 5.0f, 40.0f, 10.0f, WaypointType::Start, "Start");
    Waypoint wp1(2, 75.0f, 40.0f, 10.0f, WaypointType::Reconnaissance, "Cel");
    Waypoint returnBase(3, 5.0f, 70.0f, 10.0f, WaypointType::Return, "Baza");

    Mission mission(start, returnBase);
    mission.addTarget(wp1);
    Path path = mission.generateDirectPath(map);

    JsonExporter::save(map, "data/maps/test_1_flat.json", threatMap.getRadars(), &mission, &path);
    std::cout << "-> Zapisano: data/maps/test_1_flat.json" << std::endl;
}

void generateTestMap2_RidgeWall() {
    std::cout << "\n=== [TEST 2] Grzbiet Górski / Ściana - Weryfikacja cienia radarowego (Radar Shadow) ===" << std::endl;
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
    Path path = mission.generateDirectPath(map);

    JsonExporter::save(map, "data/maps/test_2_ridge_wall.json", threatMap.getRadars(), &mission, &path);
    std::cout << "-> Zapisano: data/maps/test_2_ridge_wall.json" << std::endl;
}

void generateTestMap3_CanyonPeaks() {
    std::cout << "\n=== [TEST 3] Szczyt vs Głęboki Kanion - Weryfikacja ukształtowania terenu ===" << std::endl;
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
    Path path = mission.generateDirectPath(map);

    JsonExporter::save(map, "data/maps/test_3_canyon_peaks.json", threatMap.getRadars(), &mission, &path);
    std::cout << "-> Zapisano: data/maps/test_3_canyon_peaks.json" << std::endl;
}

int main() {
    std::cout << "=======================================================" << std::endl;
    std::cout << "  PLANOWANIE TRAS UAV - GENEROWANIE MAP I MISJI       " << std::endl;
    std::cout << "=======================================================" << std::endl;

    generatePerlinMap();
    generateTestMap1_Flat();
    generateTestMap2_RidgeWall();
    generateTestMap3_CanyonPeaks();

    std::cout << "\n[SUKCES] Wszystkie dane i misje zostały wygenerowane pomyślnie!" << std::endl;
    return 0;
}