#include "Mission.h"

Mission::Mission(const Waypoint& start, const Waypoint& returnPoint)
    : startPoint(start), returnPoint(returnPoint) {}

void Mission::addTarget(const Waypoint& target) {
    targets.push_back(target);
}

void Mission::clearTargets() {
    targets.clear();
}

const Waypoint& Mission::getStartPoint() const {
    return startPoint;
}

const std::vector<Waypoint>& Mission::getTargets() const {
    return targets;
}

const Waypoint& Mission::getReturnPoint() const {
    return returnPoint;
}

std::vector<Waypoint> Mission::getAllWaypoints() const {
    std::vector<Waypoint> all;
    all.push_back(startPoint);
    for (const auto& t : targets) {
        all.push_back(t);
    }
    all.push_back(returnPoint);
    return all;
}

Path Mission::generateDirectPath(const Map& map) const {
    Path path;
    auto waypoints = getAllWaypoints();
    if (waypoints.size() < 2) return path;

    for (size_t i = 0; i < waypoints.size() - 1; ++i) {
        const auto& from = waypoints[i];
        const auto& to = waypoints[i + 1];

        auto segment = Path::interpolateSegment(from.x, from.y, to.x, to.y, map, from.altitudeAGL);

        size_t startIndex = (i == 0) ? 0 : 1;
        for (size_t j = startIndex; j < segment.size(); ++j) {
            path.addPoint(segment[j]);
        }
    }

    return path;
}
