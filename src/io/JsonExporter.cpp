#include "JsonExporter.h"
#include <fstream>
#include <filesystem>
#include <iostream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

void JsonExporter::save(const Map& map,
                        const std::string& filename,
                        const std::vector<RadarStation>& radars,
                        const Mission* mission,
                        const Path* path) {
    json output;

    output["width"] = map.getWidth();
    output["height"] = map.getHeight();

    // 1. Komórki terenu (Cells)
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

    // 2. Radary OPL
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

    // 3. Punkty kontrolne misji (Waypoints)
    if (mission != nullptr) {
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

    // 4. Szczegółowa ścieżka lotu UAV (dokładna lista odwiedzonych kwadratów)
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

        // Statystyki trasy
        auto stats = path->getStats(map);
        json statsJson;
        statsJson["totalDistance"] = stats.totalDistance;
        statsJson["totalThreatExposure"] = stats.totalThreatExposure;
        statsJson["maxThreatLevel"] = stats.maxThreatLevel;
        statsJson["totalVisitedCells"] = stats.totalVisitedCells;
        output["pathStats"] = statsJson;
    }

    // Zapewnienie istnienia katalogu nadrzędnego
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