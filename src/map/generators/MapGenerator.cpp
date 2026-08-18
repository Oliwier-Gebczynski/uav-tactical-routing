#include "MapGenerator.h"
#include <cmath>
#include <algorithm>

void MapGenerator::placeRoadSegment(Map& map, int x0, int y0, int x1, int y1){
    int dx = std::abs(x1 - x0);
    int dy = -std::abs(y1 - y0);

    int sx = (x0 < x1) ? 1: -1;
    int sy = (y0 < y1) ? 1: -1;

    int err = dx + dy;

    while(true){
        if(map.isInside(x0, y0)){
            Cell& cell = map.getCell(x0, y0);

            cell.terrain = TerrainType::Road;
            cell.concealment = 0.0f;
        }

        if(x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

void MapGenerator::placeBuilding(Map& map, int startX, int startY, int width, int height, float buildingHeight){
    for(int y = startY; y < startY + height; y++){
        for(int x = startX;  x < startX + width; x++){
            if(map.isInside(x,y)){
                Cell& cell = map.getCell(x,y);

                if(cell.terrain != TerrainType::Road && cell.terrain != TerrainType::Water){
                    cell.terrain = TerrainType::Building;
                    cell.elevation += buildingHeight;
                    cell.concealment = 0.0f;
                }
            }
        }
    }
}

void MapGenerator::generateProceduralMap(Map& map, int seed){
    int w = map.getWidth();
    int h = map.getHeight();

    PerlinNoise terrainElevation(seed);
    PerlinNoise forestBiome(seed + 100);
    std::mt19937 rng(seed);

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            Cell& cell = map.getCell(x, y);

            float nx = static_cast<float>(x) * 0.025f;
            float ny = static_cast<float>(y) * 0.025f;

            float rawNoise = terrainElevation.octaveNoise(nx, ny, 3, 0.5f);
            float terrainFactor = (rawNoise - 0.30f) * 3.5f; 

            float baseElevation = terrainFactor * 35.0f;

            float fx = (static_cast<float>(x) + 500.0f) * 0.035f;
            float fy = (static_cast<float>(y) + 500.0f) * 0.035f;
            float forestVal = forestBiome.noise(fx, fy);

            if (baseElevation < 0.0f) {
                cell.terrain = TerrainType::Water;
                cell.elevation = 0.0f;
                cell.concealment = 0.0f;
            } 
            else if (forestVal > 0.56f) {
                cell.terrain = TerrainType::Forest;
                float treeHeight = 10.0f + static_cast<float>(rng() % 8);
                cell.elevation = baseElevation + treeHeight;
                cell.concealment = 0.8f;
            } 
            else {
                cell.terrain = TerrainType::Grass;
                cell.elevation = baseElevation;
                cell.concealment = 0.1f;
            }
        }
    }

    int mainRoadY = h / 2;
    placeRoadSegment(map, 0, mainRoadY, w - 1, mainRoadY);

    int mainRoadX = w / 3;
    placeRoadSegment(map, mainRoadX, 0, mainRoadX, h - 1);

    placeRoadSegment(map, mainRoadX, mainRoadY + 15, w - 10, h - 10);

    std::uniform_int_distribution<int> bldgSize(3, 6);
    std::uniform_int_distribution<int> bldgFloor(2, 5);

    for (int x = 10; x < w - 10; x += 12) {
        int bW = bldgSize(rng);
        int bH = bldgSize(rng);
        float height = static_cast<float>(bldgFloor(rng) * 3);
        placeBuilding(map, x, mainRoadY - bH - 2, bW, bH, height);

        bW = bldgSize(rng);
        bH = bldgSize(rng);
        height = static_cast<float>(bldgFloor(rng) * 3);
        placeBuilding(map, x, mainRoadY + 3, bW, bH, height);
    }
}