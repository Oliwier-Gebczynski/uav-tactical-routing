#pragma once

#include <string>

enum class TerrainType{
    Grass,
    Forest,
    Road,
    Building,
    Water
};

inline std::string TerrainTypeToString(TerrainType type){
    switch(type){
        case TerrainType::Grass:
            return "grass";

        case TerrainType::Forest:
            return "forest";

        case TerrainType::Road:
            return "road";

        case TerrainType::Building:
            return "building";

        case TerrainType::Water:
            return "water";
    }

    return "unknown";
}

inline float getTerrainFeatureHeight(TerrainType type) {
    switch (type) {
        case TerrainType::Forest:
            return 12.0f;
        case TerrainType::Building:
            return 10.0f;
        case TerrainType::Grass:
        case TerrainType::Road:
        case TerrainType::Water:
        default:
            return 0.0f;
    }
}