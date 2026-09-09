#include "JsonExporter.h"
#include "../planner/CostEvaluator.h"
#include "../planner/SimulatedAnnealing.h"
#include <fstream>
#include <filesystem>
#include <iostream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

void JsonExporter::save(const Map& map,
                        const std::string& filename,
                        const std::vector<RadarStation>& radars,
                        const Mission* mission,
                        const Path* path,
                        const std::vector<Waypoint>* waypoints,
                        const std::vector<DecisionEvent>* decisionLog,
                        const SAResult* saResult) {
    json output;

    output["width"] = map.getWidth();
    output["height"] = map.getHeight();

    for (int y = 0; y < map.getHeight(); y++) {
        for (int x = 0; x < map.getWidth(); x++) {
            const Cell& cell = map.getCell(x, y);

            json c;
            c["terrain"] = TerrainTypeToString(cell.terrain);
            c["elevation"] = cell.elevation;
            c["obstacle"] = cell.obstacle;
            c["concealment"] = cell.concealment;
            c["threatLevel"] = cell.threatLevel;

            output["cells"][y][x] = c;
        }
    }

    json radarsJson = json::array();
    for (const auto& r : radars) {
        json rj;
        rj["id"] = r.id;
        rj["x"] = r.x;
        rj["y"] = r.y;
        rj["range"] = r.range;
        rj["baseThreat"] = r.baseThreat;
        rj["antennaHeight"] = r.antennaHeight;
        radarsJson.push_back(rj);
    }
    output["radars"] = radarsJson;

    if (waypoints != nullptr) {
        json missionJson;
        json waypointsJson = json::array();
        for (const auto& wp : *waypoints) {
            json wj;
            wj["id"] = wp.id;
            wj["name"] = wp.name;
            wj["type"] = WaypointTypeToString(wp.type);
            wj["x"] = wp.x;
            wj["y"] = wp.y;
            wj["altitudeAGL"] = wp.altitudeAGL;
            waypointsJson.push_back(wj);
        }
        missionJson["waypoints"] = waypointsJson;
        output["mission"] = missionJson;
    } else if (mission != nullptr) {
        json missionJson;
        json waypointsJson = json::array();
        for (const auto& wp : mission->getAllWaypoints()) {
            json wj;
            wj["id"] = wp.id;
            wj["name"] = wp.name;
            wj["type"] = WaypointTypeToString(wp.type);
            wj["x"] = wp.x;
            wj["y"] = wp.y;
            wj["altitudeAGL"] = wp.altitudeAGL;
            waypointsJson.push_back(wj);
        }
        missionJson["waypoints"] = waypointsJson;
        output["mission"] = missionJson;
    }

    if (path != nullptr && !path->empty()) {
        json pathJson = json::array();
        for (const auto& pt : path->getPoints()) {
            json pj;
            pj["x"] = pt.x;
            pj["y"] = pt.y;
            pj["z"] = pt.z;
            pathJson.push_back(pj);
        }
        output["path"] = pathJson;

        auto stats = path->getStats(map);
        CostEvaluator evaluator;
        CostBreakdown cost = evaluator.evaluate(*path, map);

        json statsJson;
        statsJson["totalDistance"] = stats.totalDistance;
        statsJson["totalThreatExposure"] = stats.totalThreatExposure;
        statsJson["effectiveThreatExposure"] = cost.threatRisk;
        statsJson["concealmentBenefit"] = cost.concealmentBenefit;
        statsJson["maxThreatLevel"] = stats.maxThreatLevel;
        statsJson["totalVisitedCells"] = stats.totalVisitedCells;
        statsJson["totalCost"] = cost.totalCost;
        statsJson["isFeasible"] = cost.isFeasible;
        statsJson["collisionCount"] = cost.collisionCount;
        statsJson["obstaclePenalty"] = cost.obstaclePenalty;
        output["pathStats"] = statsJson;

        json costJson;
        costJson["totalCost"] = cost.totalCost;
        costJson["distance"] = cost.distance;
        costJson["threatRisk"] = cost.threatRisk;
        costJson["rawThreatRisk"] = cost.rawThreatRisk;
        costJson["concealmentBenefit"] = cost.concealmentBenefit;
        costJson["obstaclePenalty"] = cost.obstaclePenalty;
        costJson["collisionCount"] = cost.collisionCount;
        costJson["buildingCollisions"] = cost.buildingCollisions;
        costJson["terrainCollisions"] = cost.terrainCollisions;
        costJson["outOfBoundsCount"] = cost.outOfBoundsCount;
        costJson["isFeasible"] = cost.isFeasible;
        costJson["weightedDistance"] = cost.weightedDistance;
        costJson["weightedThreat"] = cost.weightedThreat;
        costJson["weightedObstacle"] = cost.weightedObstacle;
        output["pathCost"] = costJson;
    }

    if (decisionLog != nullptr && !decisionLog->empty()) {
        json logJson = json::array();
        for (const auto& ev : *decisionLog) {
            json ej;
            ej["iteration"] = ev.iteration;
            ej["temperature"] = ev.temperature;
            ej["phase"] = ev.phase;
            ej["action"] = ev.action;
            ej["details"] = ev.details;
            ej["costBefore"] = ev.costBefore;
            ej["costAfter"] = ev.costAfter;
            ej["deltaCost"] = ev.deltaCost;
            logJson.push_back(ej);
        }
        output["decisionLog"] = logJson;
    }

    if (saResult != nullptr) {
        json compJson;
        auto serializeRun = [&](const AlgorithmRun& run) -> json {
            json r;
            r["name"] = run.name;
            r["key"] = run.key;
            r["totalCost"] = run.cost.totalCost;
            r["distance"] = run.cost.distance;
            r["threatRisk"] = run.cost.threatRisk;
            r["rawThreatRisk"] = run.cost.rawThreatRisk;
            r["concealmentBenefit"] = run.cost.concealmentBenefit;
            r["obstaclePenalty"] = run.cost.obstaclePenalty;
            r["collisionCount"] = run.cost.collisionCount;
            r["buildingCollisions"] = run.cost.buildingCollisions;
            r["terrainCollisions"] = run.cost.terrainCollisions;
            r["isFeasible"] = run.cost.isFeasible;
            r["waypointsCount"] = run.waypointsCount;
            r["tortuosity"] = run.tortuosity;
            r["flightTimeSec"] = run.flightTimeSec;
            r["maxThreatLevel"] = run.stats.maxThreatLevel;
            r["totalVisitedCells"] = run.stats.totalVisitedCells;

            json pArr = json::array();
            for (const auto& pt : run.path.getPoints()) {
                json pj;
                pj["x"] = pt.x;
                pj["y"] = pt.y;
                pj["z"] = pt.z;
                pArr.push_back(pj);
            }
            r["path"] = pArr;

            json wArr = json::array();
            for (const auto& wp : run.waypoints) {
                json wj;
                wj["id"] = wp.id;
                wj["name"] = wp.name;
                wj["type"] = WaypointTypeToString(wp.type);
                wj["x"] = wp.x;
                wj["y"] = wp.y;
                wj["altitudeAGL"] = wp.altitudeAGL;
                wArr.push_back(wj);
            }
            r["waypoints"] = wArr;
            return r;
        };

        compJson["baseline"] = serializeRun(saResult->baseline);
        compJson["pure_ls"] = serializeRun(saResult->pureLocalSearch);
        compJson["pure_sa"] = serializeRun(saResult->pureSA);
        compJson["sa_ls"] = serializeRun(saResult->hybridSaLs);
        output["comparison"] = compJson;

        json convJson = json::array();
        for (float c : saResult->convergenceHistory) {
            convJson.push_back(c);
        }
        output["convergence"] = convJson;

        json metJson;
        float baseCost = saResult->baseline.cost.totalCost;
        float optCost = saResult->hybridSaLs.cost.totalCost;
        float costImpPct = (baseCost > 0.001f) ? ((baseCost - optCost) / baseCost * 100.0f) : 0.0f;

        float baseThreat = saResult->baseline.cost.threatRisk;
        float optThreat = saResult->hybridSaLs.cost.threatRisk;
        float threatRedPct = (baseThreat > 0.001f) ? ((baseThreat - optThreat) / baseThreat * 100.0f) : 100.0f;

        float baseDist = saResult->baseline.cost.distance;
        float optDist = saResult->hybridSaLs.cost.distance;
        float detourPct = (baseDist > 0.001f) ? ((optDist - baseDist) / baseDist * 100.0f) : 0.0f;

        metJson["costImprovementPct"] = costImpPct;
        metJson["threatReductionPct"] = threatRedPct;
        metJson["detourPct"] = detourPct;
        metJson["totalIterations"] = saResult->totalIterations;
        metJson["acceptedBetterMoves"] = saResult->acceptedBetterMoves;
        metJson["acceptedWorseMoves"] = saResult->acceptedWorseMoves;
        metJson["rejectedMoves"] = saResult->rejectedMoves;
        metJson["saWaypointsCount"] = saResult->pureSA.waypointsCount;
        metJson["finalWaypointsCount"] = saResult->hybridSaLs.waypointsCount;
        output["metrics"] = metJson;
    }

    std::filesystem::path filePath(filename);
    if (filePath.has_parent_path()) {
        std::filesystem::create_directories(filePath.parent_path());
    }

    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Błąd zapisu pliku: " << filename << std::endl;
        return;
    }
    file << output.dump(4);
}