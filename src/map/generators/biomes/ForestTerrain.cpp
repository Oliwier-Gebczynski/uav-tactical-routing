#include "ForestTerrain.h"

ForestTerrain::ForestTerrain(int seed, float scale, float forestThreshold)
            : noise(seed), scale(scale), forestThreshold(forestThreshold) {}

void ForestTerrain::generate(Map& map, std::mt19937& rng) {
    int w = map.getWidth();
    int h = map.getHeight();

    for (int y = 0; y < h; ++y){
        for (int x = 0; x < w; ++x){
            Cell& cell = map.getCell(x, y);

            if (cell.terrain != TerrainType::Grass){
                continue;
            }

            float fx = (static_cast<float>(x) + 500.0f) * scale;
            float fy = (static_cast<float>(y) + 500.0f) * scale;
            float forestVal = noise.noise(fx, fy);

            if (forestVal > forestThreshold) {
                cell.terrain = TerrainType::Forest;
                float treeHeight = 10.0f + static_cast<float>(rng() % 8);
                cell.elevation += treeHeight;
                cell.concealment = 0.8f;
            }
        }
    }
}