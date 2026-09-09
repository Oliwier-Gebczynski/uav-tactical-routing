#pragma once

#include <vector>
#include <random>
#include <string>
#include "../map/Map.h"
#include "../routing/Mission.h"
#include "../routing/Waypoint.h"
#include "../routing/Path.h"
#include "CostEvaluator.h"
#include "LocalSearch.h"

struct SAParameters {
    float initialTemperature = 800.0f;
    float minTemperature = 0.05f;
    float coolingRate = 0.995f;
    int iterationsPerTemp = 25;
    float maxPerturbation = 12.0f;

    float probPerturb = 0.70f;
    float probInsert = 0.15f;
    float probDelete = 0.15f;
    int maxWaypoints = 25;

    bool enableLocalSearch = true;
    bool enablePeriodicLocalSearch = true;
    int localSearchInterval = 80;

    SAParameters() = default;
};

struct DecisionEvent {
    int iteration = 0;
    float temperature = 0.0f;
    std::string phase;
    std::string action;
    std::string details;
    float costBefore = 0.0f;
    float costAfter = 0.0f;
    float deltaCost = 0.0f;
};

struct AlgorithmRun {
    std::string name;
    std::string key;
    Path path;
    std::vector<Waypoint> waypoints;
    CostBreakdown cost;
    PathStats stats;
    float tortuosity = 1.0f;
    float flightTimeSec = 0.0f;
    int waypointsCount = 0;
};

struct SAResult {
    Path bestPath;
    std::vector<Waypoint> bestWaypoints;
    CostBreakdown initialCost;
    CostBreakdown bestCost;

    AlgorithmRun baseline;
    AlgorithmRun pureLocalSearch;
    AlgorithmRun pureSA;
    AlgorithmRun hybridSaLs;

    int totalIterations = 0;
    int acceptedBetterMoves = 0;
    int acceptedWorseMoves = 0;
    int rejectedMoves = 0;
    std::vector<float> convergenceHistory;
    std::vector<DecisionEvent> decisionLog;

    std::string toString() const;
};

class SimulatedAnnealing {
private:
    CostEvaluator evaluator;
    SAParameters params;

    std::vector<Waypoint> mutate(const std::vector<Waypoint>& current,
                                 const Map& map,
                                 float currentTemp,
                                 std::mt19937& rng,
                                 std::string* actionType = nullptr,
                                 std::string* actionDetail = nullptr) const;

    std::vector<Waypoint> perturbWaypoint(const std::vector<Waypoint>& current,
                                          const Map& map,
                                          float currentTemp,
                                          std::mt19937& rng,
                                          std::string* actionType = nullptr,
                                          std::string* actionDetail = nullptr) const;

    std::vector<Waypoint> insertWaypoint(const std::vector<Waypoint>& current,
                                         const Map& map,
                                         std::mt19937& rng,
                                         std::string* actionType = nullptr,
                                         std::string* actionDetail = nullptr) const;

    std::vector<Waypoint> deleteWaypoint(const std::vector<Waypoint>& current,
                                         const Map& map,
                                         std::mt19937& rng,
                                         std::string* actionType = nullptr,
                                         std::string* actionDetail = nullptr) const;

public:
    explicit SimulatedAnnealing(CostEvaluator evaluator = CostEvaluator(),
                                SAParameters params = SAParameters());

    SAResult optimize(const Mission& mission, const Map& map, unsigned int seed = 42);
    SAResult optimize(const std::vector<Waypoint>& initialWaypoints, const Map& map, unsigned int seed = 42);

    const SAParameters& getParameters() const;
    void setParameters(const SAParameters& newParams);

    const CostEvaluator& getCostEvaluator() const;
    void setCostEvaluator(const CostEvaluator& newEvaluator);
};
