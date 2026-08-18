#pragma once

#include "../Map.h"
#include "PerlinNoise.h"
#include <random>

class MapGenerator{
    public:
        static void generateProceduralMap(Map& map, int seed);
    
    private:
        static void placeRoadSegment(Map& map, int x0, int y0, int x1, int y1);
        static void placeBuilding(Map& map, int startX, int startY, int width, int height, float buildingHeight);
};