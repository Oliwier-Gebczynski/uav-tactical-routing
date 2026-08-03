#pragma once

#include "TerrainType.h"

struct Cell{
    TerrainType terrain;
    float elevation;
    bool obstacle;
    float concealment;

    Cell(){
        terrain = TerrainType::Grass;
        elevation = 0.0f;
        obstacle = false;
        concealment = 0.0f;
    }
};

