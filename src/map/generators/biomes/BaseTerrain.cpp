#include "BaseTerrain.h"

BaseTerrain::BaseTerrain(int seed, float scale, float waterLevel, float heightMulti)
            : noise(seed), scale(scale), waterLevel(waterLevel), heightMulti(heightMulti) {}

void BaseTerrain::generate(Map& map, std::mt19937& rng){
    int w = map.getWidth();
    int h = map.getHeight();

    for (int y = 0; y < h; ++y){
        for (int x = 0; x < w; ++x){
            Cell& cell = map.getCell(x, y);

            float nx = static_cast<float>(x) * scale;
            float ny = static_cast<float>(y) * scale;

            float rawNoise = noise.octaveNoise(nx, ny, 3, 0.5f);
            float terrainFactor = (rawNoise - waterLevel) * 3.5f;
            float baseElevation = terrainFactor * heightMulti;

            if(baseElevation < 0.0f){
                cell.terrain = TerrainType::Water;
                cell.elevation = 0.0f;
                cell.concealment = 0.0f;
            }else{
                cell.terrain = TerrainType::Grass;
                cell.elevation = baseElevation;
                cell.concealment = 0.1f;
            }
        }
    }
}
