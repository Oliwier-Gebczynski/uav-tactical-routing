#pragma once 

#include "../map/Map.h"
#include <string>

class JsonExporter{
    public:
        static void save(const Map& map, const std::string& filename);
};

