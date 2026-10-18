#include "ScenarioRunner.h"
#include "JsonMapImporter.h"
#include "JsonExporter.h"
#include "map/threats/ThreatMap.h"
#include "planner/SimulatedAnnealing.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>

namespace {
float bounded(const nlohmann::json& object, const char* key, float low, float high) {
    const auto& value = object.at(key);
    if (!value.is_number()) throw std::runtime_error(std::string("Expected number: ") + key);
    float result = value.get<float>();
    if (!std::isfinite(result) || result < low || result > high)
        throw std::runtime_error(std::string("Value out of range: ") + key);
    return result;
}

int integer(const nlohmann::json& object, const char* key, int low, int high) {
    if (!object.at(key).is_number_integer()) throw std::runtime_error(std::string("Expected integer: ") + key);
    auto result = object.at(key).get<std::int64_t>();
    if (result < low || result > high) throw std::runtime_error(std::string("Integer out of range: ") + key);
    return static_cast<int>(result);
}
}

void runScenario(const std::string& input, const std::string& output) {
    std::cout << "[1/4] Wczytywanie i walidacja scenariusza" << std::endl;
    std::ifstream file(input);
    if (!file) throw std::runtime_error("Cannot open scenario: " + input);
    auto document = nlohmann::json::parse(file);
    Map map = JsonMapImporter::fromJson(document, true);
    // A million-cell JSON tree is large; the planner now owns the terrain.
    document.erase("cells");
    const auto& config = document.at("scenario");
    if (config.at("schemaVersion") != 1) throw std::runtime_error("Unsupported scenario schema");
    const int seed = integer(config, "seed", 0, 2147483647);
    const float altitude = bounded(config, "flightAltitude", 0.1f, 1000);
    const auto& optimizer = config.at("optimizer");
    SAParameters params;
    params.initialTemperature = bounded(optimizer, "initialTemperature", 0.1f, 10000);
    params.minTemperature = bounded(optimizer, "minTemperature", 0.001f, params.initialTemperature);
    if (params.minTemperature >= params.initialTemperature) throw std::runtime_error("Minimum temperature must be lower than initial");
    params.coolingRate = bounded(optimizer, "coolingRate", 0.1f, 0.9999f);
    params.iterationsPerTemp = integer(optimizer, "iterationsPerTemp", 1, 1000);
    params.maxPerturbation = bounded(optimizer, "maxPerturbation", 0.1f, 1000);
    params.maxWaypoints = integer(optimizer, "maxWaypoints", 2, 200);
    params.enableLocalSearch = optimizer.at("enableLocalSearch").get<bool>();
    params.enablePeriodicLocalSearch = optimizer.at("enablePeriodicLocalSearch").get<bool>();
    params.localSearchInterval = integer(optimizer, "localSearchInterval", 1, 100000);
    params.probPerturb = bounded(optimizer, "probPerturb", 0, 1);
    params.probInsert = bounded(optimizer, "probInsert", 0, 1);
    params.probDelete = bounded(optimizer, "probDelete", 0, 1);
    if (std::abs(params.probPerturb + params.probInsert + params.probDelete - 1) > 0.0001f)
        throw std::runtime_error("Mutation probabilities must sum to one");
    const double steps = std::ceil(std::log(params.minTemperature / params.initialTemperature) / std::log(params.coolingRate));
    if (steps * params.iterationsPerTemp > 2000000)
        throw std::runtime_error("Optimizer configuration exceeds 2000000 iterations");
    const auto& weightsJson = config.at("weights");
    CostWeights weights;
    weights.distanceWeight = bounded(weightsJson, "distanceWeight", 0, 1000000);
    weights.threatWeight = bounded(weightsJson, "threatWeight", 0, 1000000);
    weights.obstacleWeight = bounded(weightsJson, "obstacleWeight", 0, 1000000);
    weights.baseCollisionPenalty = bounded(weightsJson, "baseCollisionPenalty", 0, 1000000);
    weights.altitudeSafetyMargin = bounded(weightsJson, "altitudeSafetyMargin", 0, 1000);

    const auto& inputMission = document.contains("inputMission") ? document.at("inputMission") : document.at("mission");
    const auto& points = inputMission.at("waypoints");
    if (!points.is_array() || points.size() < 2 || points.size() > 100)
        throw std::runtime_error("Mission needs start, end and at most 98 checkpoints");
    std::vector<Waypoint> waypoints;
    std::set<int> waypointIds;
    for (size_t i = 0; i < points.size(); ++i) {
        const auto& point = points[i];
        int id = integer(point, "id", 1, 999);
        if (!waypointIds.insert(id).second) throw std::runtime_error("Duplicate waypoint id");
        const auto type = point.at("type").get<std::string>();
        const auto expected = i == 0 ? "start" : (i == points.size() - 1 ? "return" : "reconnaissance");
        if (type != expected) throw std::runtime_error("Waypoints must be ordered: start, checkpoints, return");
        const float x = bounded(point, "x", 0, map.getWidth() - 1);
        const float y = bounded(point, "y", 0, map.getHeight() - 1);
        if (std::abs(bounded(point, "altitudeAGL", 0.1f, 1000) - altitude) > 0.001f)
            throw std::runtime_error("Current planner requires a shared flight altitude");
        waypoints.emplace_back(id, x, y, altitude, i == 0 ? WaypointType::Start :
            (i == points.size() - 1 ? WaypointType::Return : WaypointType::Reconnaissance), point.value("name", type));
    }
    if (static_cast<int>(waypoints.size()) > params.maxWaypoints)
        throw std::runtime_error("maxWaypoints must include all mission points");
    const auto& radarList = document.at("radars");
    if (!radarList.is_array() || radarList.size() > 100) throw std::runtime_error("At most 100 radars are supported");
    ThreatMap threats;
    std::set<int> radarIds;
    for (const auto& radar : radarList) {
        const int id = integer(radar, "id", 1, 1000000);
        if (!radarIds.insert(id).second) throw std::runtime_error("Duplicate radar id");
        threats.addRadar(RadarStation(id, integer(radar, "x", 0, map.getWidth() - 1),
            integer(radar, "y", 0, map.getHeight() - 1), bounded(radar, "range", 1, 2000),
            bounded(radar, "baseThreat", 0, 1), bounded(radar, "antennaHeight", 0, 1000)));
    }
    std::cout << "[2/4] Obliczanie pola radarowego" << std::endl;
    threats.calculateThreats(map, altitude);
    std::cout << "[3/4] Porównanie: prosta / Local Search / SA / SA+LS; seed=" << seed << std::endl;
    CostEvaluator evaluator(weights);
    SimulatedAnnealing annealing(evaluator, params);
    const auto result = annealing.optimize(waypoints, map, static_cast<unsigned int>(seed));
    Mission mission(waypoints.front(), waypoints.back());
    for (size_t i = 1; i + 1 < waypoints.size(); ++i) mission.addTarget(waypoints[i]);
    std::cout << "[4/4] Zapisywanie wyników" << std::endl;
    JsonExporter::save(map, output, threats.getRadars(), &mission, &result.bestPath,
                       &result.bestWaypoints, &result.decisionLog, &result, &config);
    std::cout << "Wynik: " << output << std::endl;
}
