#include "Path.h"
#include <cmath>
#include <algorithm>

void Path::addPoint(const Point3D& pt) {
    points.push_back(pt);
}

void Path::addPoint(float x, float y, float z) {
    points.emplace_back(x, y, z);
}

void Path::clear() {
    points.clear();
}

const std::vector<Point3D>& Path::getPoints() const {
    return points;
}

size_t Path::size() const {
    return points.size();
}

bool Path::empty() const {
    return points.empty();
}

float Path::calculateTotalDistance() const {
    if (points.size() < 2) return 0.0f;
    float total = 0.0f;
    for (size_t i = 1; i < points.size(); ++i) {
        float dx = points[i].x - points[i - 1].x;
        float dy = points[i].y - points[i - 1].y;
        float dz = points[i].z - points[i - 1].z;
        total += std::sqrt(dx * dx + dy * dy + dz * dz);
    }
    return total;
}

float Path::calculateTotalThreatCost(const Map& map) const {
    float totalThreat = 0.0f;
    for (const auto& pt : points) {
        int ix = static_cast<int>(std::round(pt.x));
        int iy = static_cast<int>(std::round(pt.y));
        if (map.isInside(ix, iy)) {
            totalThreat += map.getCell(ix, iy).threatLevel;
        }
    }
    return totalThreat;
}

float Path::calculateMaxThreat(const Map& map) const {
    float maxThreat = 0.0f;
    for (const auto& pt : points) {
        int ix = static_cast<int>(std::round(pt.x));
        int iy = static_cast<int>(std::round(pt.y));
        if (map.isInside(ix, iy)) {
            maxThreat = std::max(maxThreat, map.getCell(ix, iy).threatLevel);
        }
    }
    return maxThreat;
}

PathStats Path::getStats(const Map& map) const {
    PathStats stats;
    stats.totalDistance = calculateTotalDistance();
    stats.totalThreatExposure = calculateTotalThreatCost(map);
    stats.maxThreatLevel = calculateMaxThreat(map);
    stats.totalVisitedCells = static_cast<int>(points.size());
    return stats;
}

std::vector<Point3D> Path::interpolateSegment(float x0, float y0, float x1, float y1,
                                              const Map& map, float uavAltitudeAGL) {
    std::vector<Point3D> segment;

    int ix0 = static_cast<int>(std::round(x0));
    int iy0 = static_cast<int>(std::round(y0));
    int ix1 = static_cast<int>(std::round(x1));
    int iy1 = static_cast<int>(std::round(y1));

    int dx = std::abs(ix1 - ix0);
    int dy = std::abs(iy1 - iy0);
    int sx = (ix0 < ix1) ? 1 : -1;
    int sy = (iy0 < iy1) ? 1 : -1;

    int x = ix0;
    int y = iy0;
    int err = dx - dy;

    while (true) {
        if (map.isInside(x, y)) {
            float elev = map.getCell(x, y).elevation;
            segment.emplace_back(static_cast<float>(x), static_cast<float>(y), elev + uavAltitudeAGL);
        }

        if (x == ix1 && y == iy1) {
            break;
        }

        int e2 = 2 * err;
        if (e2 > -dy) {
            err -= dy;
            x += sx;
        }
        if (e2 < dx) {
            err += dx;
            y += sy;
        }
    }

    return segment;
}
