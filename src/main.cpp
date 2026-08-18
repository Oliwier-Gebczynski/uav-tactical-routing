#include <iostream>
#include "map/Map.h"
#include "map/generators/MapGenerator.h"
#include "io/JsonExporter.h"

int main() {
    std::cout << "1. Tworzenie siatki mapy 100x100..." << std::endl;
    Map map(100, 100);

    std::cout << "2. Generowanie realistycznego terenu (rzeki, lasy, drogi, budynki)..." << std::endl;
    MapGenerator::generateProceduralMap(map, 67);

    std::cout << "3. Eksport mapy do JSON..." << std::endl;
    JsonExporter::save(map, "data/maps/perlin_full_test_map.json");

    std::cout << "Gotowe! Wynik zapisano w data/maps/test_map.json" << std::endl;
    return 0;
}