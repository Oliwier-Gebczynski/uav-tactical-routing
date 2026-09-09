#pragma once

#include <vector>
#include "Waypoint.h"
#include "../map/Map.h"

struct PathStats {
    float totalDistance = 0.0f;
    float totalThreatExposure = 0.0f;
    float maxThreatLevel = 0.0f;
    int totalVisitedCells = 0;
};

class Path {
private:
    std::vector<Point3D> points;

public:
    Path() = default;

    void addPoint(const Point3D& pt);
    void addPoint(float x, float y, float z = 0.0f);
    void clear();

    const std::vector<Point3D>& getPoints() const;
    size_t size() const;
    bool empty() const;

    float calculateTotalDistance() const;
    float calculateTotalThreatCost(const Map& map) const;
    float calculateMaxThreat(const Map& map) const;
    PathStats getStats(const Map& map) const;

    static std::vector<Point3D> interpolateSegment(float x0, float y0, float x1, float y1,
                                                  const Map& map, float uavAltitudeAGL = 10.0f);
};
