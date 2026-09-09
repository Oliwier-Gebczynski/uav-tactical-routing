#pragma once

#include <vector>
#include "../map/Map.h"
#include "../routing/Waypoint.h"
#include "../routing/Path.h"
#include "CostEvaluator.h"

struct LocalSearchConfig {
    int maxPasses = 4;
    float perturbationStep = 1.0f;
    bool enableShortcutting = true;
    bool enableSmoothing = true;
    bool enableFineTuning = true;

    LocalSearchConfig() = default;
};

class LocalSearch {
public:

    static std::vector<Waypoint> optimize(const std::vector<Waypoint>& waypoints,
                                          const Map& map,
                                          const CostEvaluator& evaluator,
                                          const LocalSearchConfig& config = LocalSearchConfig());

    static std::vector<Waypoint> shortcutting(const std::vector<Waypoint>& waypoints,
                                              const Map& map,
                                              const CostEvaluator& evaluator);

    static std::vector<Waypoint> smooth(const std::vector<Waypoint>& waypoints,
                                        const Map& map,
                                        const CostEvaluator& evaluator);

    static std::vector<Waypoint> fineTune(const std::vector<Waypoint>& waypoints,
                                          const Map& map,
                                          const CostEvaluator& evaluator,
                                          float step = 1.0f);

    static Path buildDensePath(const std::vector<Waypoint>& waypoints, const Map& map);
};
