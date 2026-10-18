#pragma once

#include "../map/Map.h"
#include "../map/threats/RadarStation.h"
#include "../routing/Waypoint.h"
#include "../routing/Path.h"
#include "../routing/Mission.h"
#include <string>
#include <vector>

struct DecisionEvent;
struct SAResult;

class JsonExporter {
public:
    static void save(const Map& map,
                     const std::string& filename,
                     const std::vector<RadarStation>& radars = {},
                     const Mission* mission = nullptr,
                     const Path* path = nullptr,
                     const std::vector<Waypoint>* waypoints = nullptr,
                     const std::vector<DecisionEvent>* decisionLog = nullptr,
                     const SAResult* saResult = nullptr,
                     const nlohmann::json* runConfig = nullptr);
};
