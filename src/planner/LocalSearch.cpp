#include "LocalSearch.h"
#include <cmath>
#include <algorithm>

Path LocalSearch::buildDensePath(const std::vector<Waypoint>& waypoints, const Map& map) {
    Path path;
    if (waypoints.size() < 2) return path;

    for (size_t i = 0; i < waypoints.size() - 1; ++i) {
        const auto& from = waypoints[i];
        const auto& to = waypoints[i + 1];

        auto segment = Path::interpolateSegment(from.x, from.y, to.x, to.y, map, from.altitudeAGL);
        size_t startIdx = (i == 0) ? 0 : 1;
        for (size_t j = startIdx; j < segment.size(); ++j) {
            path.addPoint(segment[j]);
        }
    }
    return path;
}

std::vector<Waypoint> LocalSearch::shortcutting(const std::vector<Waypoint>& waypoints,
                                                const Map& map,
                                                const CostEvaluator& evaluator) {
    if (waypoints.size() <= 2) {
        return waypoints;
    }

    std::vector<Waypoint> result;
    result.push_back(waypoints[0]);

    size_t currentIndex = 0;
    while (currentIndex < waypoints.size() - 1) {
        size_t bestNextIndex = currentIndex + 1;

        for (size_t j = waypoints.size() - 1; j > currentIndex + 1; --j) {

            bool containsTarget = false;
            for (size_t k = currentIndex + 1; k < j; ++k) {
                if (waypoints[k].type == WaypointType::Reconnaissance) {
                    containsTarget = true;
                    break;
                }
            }
            if (containsTarget) {
                continue;
            }

            auto directSegment = Path::interpolateSegment(waypoints[currentIndex].x,
                                                          waypoints[currentIndex].y,
                                                          waypoints[j].x,
                                                          waypoints[j].y,
                                                          map,
                                                          waypoints[currentIndex].altitudeAGL);

            CostBreakdown directCost = evaluator.evaluate(directSegment, map);
            if (!directCost.isFeasible) {
                continue;
            }

            std::vector<Waypoint> subWaypoints(waypoints.begin() + currentIndex, waypoints.begin() + j + 1);
            Path subPath = buildDensePath(subWaypoints, map);
            CostBreakdown subCost = evaluator.evaluate(subPath, map);

            if (directCost.totalCost <= subCost.totalCost + 0.01f) {
                bestNextIndex = j;
                break;
            }
        }

        result.push_back(waypoints[bestNextIndex]);
        currentIndex = bestNextIndex;
    }

    return result;
}

std::vector<Waypoint> LocalSearch::fineTune(const std::vector<Waypoint>& waypoints,
                                            const Map& map,
                                            const CostEvaluator& evaluator,
                                            float step) {
    if (waypoints.size() <= 2) {
        return waypoints;
    }

    std::vector<Waypoint> current = waypoints;
    float currentCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);

    const float dx[] = {-step, step, 0.0f, 0.0f, -step, -step, step, step};
    const float dy[] = {0.0f, 0.0f, -step, step, -step, step, -step, step};

    int w = map.getWidth();
    int h = map.getHeight();

    for (size_t i = 1; i < current.size() - 1; ++i) {

        if (current[i].type != WaypointType::Transit) {
            continue;
        }

        float bestX = current[i].x;
        float bestY = current[i].y;
        float bestStepCost = currentCost;

        for (int d = 0; d < 8; ++d) {
            float nx = current[i].x + dx[d];
            float ny = current[i].y + dy[d];

            if (nx < 1.0f || nx >= w - 1 || ny < 1.0f || ny >= h - 1) {
                continue;
            }

            std::vector<Waypoint> candidate = current;
            candidate[i].x = nx;
            candidate[i].y = ny;

            Path candPath = buildDensePath(candidate, map);
            CostBreakdown candCost = evaluator.evaluate(candPath, map);

            if (candCost.isFeasible && candCost.totalCost < bestStepCost) {
                bestStepCost = candCost.totalCost;
                bestX = nx;
                bestY = ny;
            }
        }

        if (bestStepCost < currentCost) {
            current[i].x = bestX;
            current[i].y = bestY;
            currentCost = bestStepCost;
        }
    }

    return current;
}

std::vector<Waypoint> LocalSearch::smooth(const std::vector<Waypoint>& waypoints,
                                         const Map& map,
                                         const CostEvaluator& evaluator) {
    if (waypoints.size() <= 2) {
        return waypoints;
    }

    std::vector<Waypoint> current = waypoints;
    float currentCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);

    int w = map.getWidth();
    int h = map.getHeight();

    for (size_t i = 1; i < current.size() - 1; ++i) {
        if (current[i].type != WaypointType::Transit) {
            continue;
        }

        float smoothX = 0.5f * current[i].x + 0.25f * (current[i - 1].x + current[i + 1].x);
        float smoothY = 0.5f * current[i].y + 0.25f * (current[i - 1].y + current[i + 1].y);

        if (smoothX < 1.0f || smoothX >= w - 1 || smoothY < 1.0f || smoothY >= h - 1) {
            continue;
        }

        std::vector<Waypoint> candidate = current;
        candidate[i].x = smoothX;
        candidate[i].y = smoothY;

        Path candPath = buildDensePath(candidate, map);
        CostBreakdown candCost = evaluator.evaluate(candPath, map);

        if (candCost.isFeasible && candCost.totalCost <= currentCost + 0.05f) {
            current[i].x = smoothX;
            current[i].y = smoothY;
            currentCost = candCost.totalCost;
        }
    }

    return current;
}

std::vector<Waypoint> LocalSearch::optimize(const std::vector<Waypoint>& waypoints,
                                            const Map& map,
                                            const CostEvaluator& evaluator,
                                            const LocalSearchConfig& config) {
    std::vector<Waypoint> current = waypoints;
    float bestCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);

    for (int pass = 0; pass < config.maxPasses; ++pass) {
        float costBeforePass = bestCost;

        if (config.enableShortcutting) {
            current = shortcutting(current, map, evaluator);
            bestCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);
        }

        if (config.enableFineTuning) {
            current = fineTune(current, map, evaluator, config.perturbationStep);
            bestCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);
        }

        if (config.enableSmoothing) {
            current = smooth(current, map, evaluator);
            bestCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);
        }

        if (config.enableShortcutting) {
            current = shortcutting(current, map, evaluator);
            bestCost = evaluator.evaluateTotalCost(buildDensePath(current, map), map);
        }

        if (std::abs(costBeforePass - bestCost) < 0.001f) {
            break;
        }
    }

    return current;
}
