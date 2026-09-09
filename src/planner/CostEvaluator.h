#pragma once

#include <vector>
#include <string>
#include <ostream>
#include "../map/Map.h"
#include "../routing/Path.h"
#include "../routing/Waypoint.h"

struct CostWeights {
    float distanceWeight = 1.0f;
    float threatWeight = 50.0f;
    float obstacleWeight = 10000.0f;
    float baseCollisionPenalty = 100.0f;
    float altitudeSafetyMargin = 0.0f;

    CostWeights() = default;
    CostWeights(float w1, float w2, float w3,
                float basePenalty = 100.0f, float safetyMargin = 0.0f)
        : distanceWeight(w1), threatWeight(w2), obstacleWeight(w3),
          baseCollisionPenalty(basePenalty), altitudeSafetyMargin(safetyMargin) {}
};

struct CostBreakdown {

    float totalCost = 0.0f;

    float distance = 0.0f;
    float threatRisk = 0.0f;
    float rawThreatRisk = 0.0f;
    float concealmentBenefit = 0.0f;
    float obstaclePenalty = 0.0f;

    int totalPoints = 0;
    int collisionCount = 0;
    int outOfBoundsCount = 0;
    int buildingCollisions = 0;
    int terrainCollisions = 0;
    bool isFeasible = true;

    float weightedDistance = 0.0f;
    float weightedThreat = 0.0f;
    float weightedObstacle = 0.0f;

    std::string toString() const;
};

class CostEvaluator {
private:
    CostWeights weights;

public:
    explicit CostEvaluator(CostWeights weights = CostWeights());
    CostEvaluator(float w1, float w2, float w3);

    CostBreakdown evaluate(const Path& path, const Map& map) const;
    CostBreakdown evaluate(const std::vector<Point3D>& points, const Map& map) const;
    float evaluateTotalCost(const Path& path, const Map& map) const;

    float evaluateStepCost(const Point3D& from, const Point3D& to, const Map& map) const;
    float evaluatePointThreat(int x, int y, const Map& map) const;
    float evaluatePointThreat(const Point3D& pt, const Map& map) const;

    bool isPointInCollision(const Point3D& pt, const Map& map) const;
    bool isSegmentInCollision(const Point3D& from, const Point3D& to, const Map& map) const;

    const CostWeights& getWeights() const;
    void setWeights(const CostWeights& newWeights);
    void setWeights(float w1, float w2, float w3);
    void setDistanceWeight(float w1);
    void setThreatWeight(float w2);
    void setObstacleWeight(float w3);
    void setBaseCollisionPenalty(float penalty);
    void setAltitudeSafetyMargin(float margin);
};
