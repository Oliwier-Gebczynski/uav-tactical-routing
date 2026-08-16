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