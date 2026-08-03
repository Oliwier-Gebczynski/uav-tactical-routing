#pragma once

#include <string>

enum class TerrainType{
    Grass,
    Field,
    Forest,
    Road,
    Building,
    Water
};

inline std::string TerrainTypeToString(TerrainType type){
    switch(type){
        case TerrainType::Grass:
            return "grass";

        case TerrainType::Field:
            return "field";

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