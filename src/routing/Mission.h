#pragma once

#include <vector>
#include <string>
#include "Waypoint.h"
#include "Path.h"
#include "../map/Map.h"

class Mission {
private:
    Waypoint startPoint;
    std::vector<Waypoint> targets;
    Waypoint returnPoint;

public:
    Mission(const Waypoint& start, const Waypoint& returnPoint);

    void addTarget(const Waypoint& target);
    void clearTargets();

    const Waypoint& getStartPoint() const;
    const std::vector<Waypoint>& getTargets() const;
    const Waypoint& getReturnPoint() const;

    std::vector<Waypoint> getAllWaypoints() const;

    Path generateDirectPath(const Map& map) const;
};
