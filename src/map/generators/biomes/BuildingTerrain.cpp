#include "BuildingTerrain.h"

void BuildingTerrain::placeBuilding(Map& map, int startX, int startY, int width, int height, float buildingHeight){
    for (int y = startY; y < startY + height; y++){
        for (int x = startX; x < startX + width; x++){
            if (map.isInside(x, y)){
                Cell& cell = map.getCell(x, y);

                if (cell.terrain != TerrainType::Road && cell.terrain != TerrainType::Water){
                    cell.terrain = TerrainType::Building;
                    cell.elevation += buildingHeight;
                    cell.concealment = 0.0f;
                }
            }
        }
    }
}

void BuildingTerrain::generate(Map& map, std::mt19937& rng){
    int w = map.getWidth();
    int h = map.getHeight();
    int mainRoadY = h / 2;

    std::uniform_int_distribution<int> bldgSize(3, 6);
    std::uniform_int_distribution<int> bldgFloor(2, 5);

    for (int x = 10; x < w - 10; x += 12){
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