#include <iostream>
#include <algorithm>
#include "map/Map.h"
#include "map/generators/PerlinNoise.h"
#include "io/JsonExporter.h"

int main() {
    const int WIDTH = 100;
    const int HEIGHT = 100;

    std::cout << "1. Tworzenie mapy " << WIDTH << "x" << HEIGHT << "..." << std::endl;
    Map map(WIDTH, HEIGHT);

    PerlinNoise perlin(1337);

    std::cout << "2. Generowanie uksztaltowania wysokosci z uzyciem PerlinNoise..." << std::endl;
    
    float minElevation = 9999.0f;
    float maxElevation = -9999.0f;

    for (int y = 0; y < HEIGHT; ++y) {
        for (int x = 0; x < WIDTH; ++x) {
            float nx = static_cast<float>(x) * 0.05f;
            float ny = static_cast<float>(y) * 0.05f;

            float noiseVal = perlin.octaveNoise(nx, ny, 4, 0.5f);

            float elevation = noiseVal * 25.0f;

            Cell& cell = map.getCell(x, y);
            cell.elevation = elevation;

            if (elevation < 4.0f) {
                cell.terrain = TerrainType::Water;
                cell.concealment = 0.0f;
            } else {
                cell.terrain = TerrainType::Grass;
                cell.concealment = 0.1f;
            }

            minElevation = std::min(minElevation, elevation);
            maxElevation = std::max(maxElevation, elevation);
        }
    }

    std::cout << "   -> Wygenerowano wysokosci: Min = " << minElevation 
              << " m, Max = " << maxElevation << " m" << std::endl;

    std::cout << "3. Eksport mapy do JSON..." << std::endl;
    JsonExporter::save(
        map,
        "data/maps/perlin_test_map.json"
    );

    std::cout << "Sukces! Sprawdz plik data/maps/perlin_test_map.json" << std::endl;
    return 0;
}