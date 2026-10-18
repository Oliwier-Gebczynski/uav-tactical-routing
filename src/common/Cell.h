#pragma once

#include "TerrainType.h"
#include <optional>

struct Cell{
    TerrainType terrain;
    float elevation;
    bool obstacle;
    float concealment;
    float threatLevel;
    // Imported maps retain ground separately; elevation stays the obstacle top
    // used by the existing planner and legacy map files.
    std::optional<float> groundElevation;
    bool landCoverKnown = true;
    std::string buildingId;

    Cell(){
        terrain = TerrainType::Grass;
        elevation = 0.0f;
        obstacle = false;
        concealment = 0.0f;
        threatLevel = 0.0f;
    }
};
