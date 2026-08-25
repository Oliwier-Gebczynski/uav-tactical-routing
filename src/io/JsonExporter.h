#pragma once

#include "../map/Map.h"
#include "../map/threats/RadarStation.h"
#include "../routing/Waypoint.h"
#include "../routing/Path.h"
#include "../routing/Mission.h"
#include <string>
#include <vector>

class JsonExporter {
public:
    static void save(const Map& map,
                     const std::string& filename,
                     const std::vector<RadarStation>& radars = {},
                     const Mission* mission = nullptr,
                     const Path* path = nullptr);
};