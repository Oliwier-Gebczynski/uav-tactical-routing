#include "CostEvaluator.h"
#include <cmath>
#include <sstream>
#include <iomanip>
#include <algorithm>

std::string CostBreakdown::toString() const {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2);
    oss << "=== [RAPORT KOSZTU TRASY UAV] ===\n";
    oss << "  Status: " << (isFeasible ? "WYKONALNA (BEZPIECZNA)" : "NIEWYKONALNA (WYKRYTO KOLIZJE)") << "\n";
    oss << "  Łączny Koszt E(Path): " << totalCost << "\n";
    oss << "  -----------------------------------------\n";
    oss << "  1. Długość trasy L(Path):    " << distance << " m  (ważony: " << weightedDistance << ")\n";
    oss << "  2. Zagrożenie OPL R(Path):   " << threatRisk << "  (ważony: " << weightedThreat << ")\n";
    oss << "     - Surowe zagrożenie:      " << rawThreatRisk << "\n";
    oss << "     - Zysk z maskowania:      " << concealmentBenefit << " ("
        << (rawThreatRisk > 0.0001f ? (concealmentBenefit / rawThreatRisk * 100.0f) : 0.0f) << "% redukcji)\n";
    oss << "  3. Kary za przeszkody P(Path): " << obstaclePenalty << "  (ważony: " << weightedObstacle << ")\n";
    oss << "     - Liczba kolizji:         " << collisionCount << " / " << totalPoints << " punktów\n";
    if (buildingCollisions > 0) {
        oss << "     - Kolizje z budynkami:    " << buildingCollisions << "\n";
    }
    if (terrainCollisions > 0) {
        oss << "     - Kolizje z terenem:      " << terrainCollisions << "\n";
    }
    if (outOfBoundsCount > 0) {
        oss << "     - Punkty poza mapą:       " << outOfBoundsCount << "\n";
    }
    oss << "=========================================";
    return oss.str();
}

CostEvaluator::CostEvaluator(CostWeights weights)
    : weights(weights) {}

CostEvaluator::CostEvaluator(float w1, float w2, float w3)
    : weights(w1, w2, w3) {}

CostBreakdown CostEvaluator::evaluate(const std::vector<Point3D>& points, const Map& map) const {
    CostBreakdown breakdown;
    breakdown.totalPoints = static_cast<int>(points.size());

    if (points.empty()) {
        breakdown.isFeasible = true;
        return breakdown;
    }

    float totalDistance = 0.0f;
    for (size_t i = 1; i < points.size(); ++i) {
        float dx = points[i].x - points[i - 1].x;
        float dy = points[i].y - points[i - 1].y;
        float dz = points[i].z - points[i - 1].z;
        totalDistance += std::sqrt(dx * dx + dy * dy + dz * dz);
    }
    breakdown.distance = totalDistance;

    for (const auto& pt : points) {
        int ix = static_cast<int>(std::round(pt.x));
        int iy = static_cast<int>(std::round(pt.y));

        if (!map.isInside(ix, iy)) {

            breakdown.outOfBoundsCount++;
            breakdown.collisionCount++;
            breakdown.obstaclePenalty += weights.baseCollisionPenalty * 2.0f;
            continue;
        }

        const Cell& cell = map.getCell(ix, iy);

        float threat = cell.threatLevel;
        float concealment = std::clamp(cell.concealment, 0.0f, 1.0f);
        float effectiveThreat = threat * (1.0f - concealment);

        breakdown.threatRisk += effectiveThreat;
        breakdown.rawThreatRisk += threat;
        breakdown.concealmentBenefit += (threat - effectiveThreat);

        bool hasCollision = false;
        float safeElevation = cell.elevation + weights.altitudeSafetyMargin;

        if (pt.z <= safeElevation) {
            hasCollision = true;
            breakdown.terrainCollisions++;
            float penetration = safeElevation - pt.z;
            breakdown.obstaclePenalty += weights.baseCollisionPenalty + penetration * 10.0f;
        }

        if (cell.terrain == TerrainType::Building && pt.z <= cell.elevation) {
            breakdown.buildingCollisions++;
            if (!hasCollision) {
                hasCollision = true;
                breakdown.obstaclePenalty += weights.baseCollisionPenalty;
            }
            breakdown.obstaclePenalty += weights.baseCollisionPenalty * 1.5f;
        }

        if (cell.obstacle) {
            if (!hasCollision) {
                hasCollision = true;
                breakdown.obstaclePenalty += weights.baseCollisionPenalty;
            }
        }

        if (hasCollision) {
            breakdown.collisionCount++;
        }
    }

    breakdown.isFeasible = (breakdown.collisionCount == 0 && breakdown.outOfBoundsCount == 0);
    breakdown.weightedDistance = weights.distanceWeight * breakdown.distance;
    breakdown.weightedThreat = weights.threatWeight * breakdown.threatRisk;
    breakdown.weightedObstacle = weights.obstacleWeight * breakdown.obstaclePenalty;

    breakdown.totalCost = breakdown.weightedDistance + breakdown.weightedThreat + breakdown.weightedObstacle;

    return breakdown;
}

CostBreakdown CostEvaluator::evaluate(const Path& path, const Map& map) const {
    return evaluate(path.getPoints(), map);
}

float CostEvaluator::evaluateTotalCost(const Path& path, const Map& map) const {
    return evaluate(path, map).totalCost;
}

float CostEvaluator::evaluateStepCost(const Point3D& from, const Point3D& to, const Map& map) const {
    float dx = to.x - from.x;
    float dy = to.y - from.y;
    float dz = to.z - from.z;
    float stepDist = std::sqrt(dx * dx + dy * dy + dz * dz);

    float threat = evaluatePointThreat(to, map);
    bool collides = isPointInCollision(to, map);
    float penalty = collides ? weights.baseCollisionPenalty : 0.0f;

    return weights.distanceWeight * stepDist +
           weights.threatWeight * threat +
           weights.obstacleWeight * penalty;
}

float CostEvaluator::evaluatePointThreat(int x, int y, const Map& map) const {
    if (!map.isInside(x, y)) {
        return 0.0f;
    }
    const Cell& cell = map.getCell(x, y);
    float concealment = std::clamp(cell.concealment, 0.0f, 1.0f);
    return cell.threatLevel * (1.0f - concealment);
}

float CostEvaluator::evaluatePointThreat(const Point3D& pt, const Map& map) const {
    int ix = static_cast<int>(std::round(pt.x));
    int iy = static_cast<int>(std::round(pt.y));
    return evaluatePointThreat(ix, iy, map);
}

bool CostEvaluator::isPointInCollision(const Point3D& pt, const Map& map) const {
    int ix = static_cast<int>(std::round(pt.x));
    int iy = static_cast<int>(std::round(pt.y));

    if (!map.isInside(ix, iy)) {
        return true;
    }

    const Cell& cell = map.getCell(ix, iy);
    float safeElevation = cell.elevation + weights.altitudeSafetyMargin;

    if (pt.z <= safeElevation) {
        return true;
    }
    if (cell.terrain == TerrainType::Building && pt.z <= cell.elevation) {
        return true;
    }
    if (cell.obstacle) {
        return true;
    }

    return false;
}

bool CostEvaluator::isSegmentInCollision(const Point3D& from, const Point3D& to, const Map& map) const {
    auto pts = Path::interpolateSegment(from.x, from.y, to.x, to.y, map, from.z);
    for (const auto& p : pts) {
        if (isPointInCollision(p, map)) {
            return true;
        }
    }
    return false;
}

const CostWeights& CostEvaluator::getWeights() const {
    return weights;
}

void CostEvaluator::setWeights(const CostWeights& newWeights) {
    weights = newWeights;
}

void CostEvaluator::setWeights(float w1, float w2, float w3) {
    weights.distanceWeight = w1;
    weights.threatWeight = w2;
    weights.obstacleWeight = w3;
}

void CostEvaluator::setDistanceWeight(float w1) {
    weights.distanceWeight = w1;
}

void CostEvaluator::setThreatWeight(float w2) {
    weights.threatWeight = w2;
}

void CostEvaluator::setObstacleWeight(float w3) {
    weights.obstacleWeight = w3;
}

void CostEvaluator::setBaseCollisionPenalty(float penalty) {
    weights.baseCollisionPenalty = penalty;
}

void CostEvaluator::setAltitudeSafetyMargin(float margin) {
    weights.altitudeSafetyMargin = margin;
}
