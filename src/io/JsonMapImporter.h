#pragma once

#include "../map/Map.h"
#include <string>

class JsonMapImporter {
public:
    // Loads the 1 m grid written by python/main.py import-map. Invalid or
    // incomplete data is rejected before it can enter the planner.
    static Map load(const std::string& filename);
    static Map fromJson(const nlohmann::json& data, bool allowLegacy = false);
};
