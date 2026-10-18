#include "io/JsonMapImporter.h"
#include "map/threats/ThreatMap.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <functional>
#include <chrono>

int main() {
    using nlohmann::json;
    const auto path = std::filesystem::temp_directory_path() /
        ("uav-import-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + ".json");
    auto write = [&](const json& data) { std::ofstream(path) << data; };
    json cell = {{"terrain", "building"}, {"elevation", 120}, {"groundElevation", 100},
                 {"obstacleHeight", 20}, {"concealment", 0}, {"threatLevel", 0},
                 {"obstacle", false}, {"landCoverKnown", true}, {"buildingId", "way/1"}};
    json valid = {{"width", 1}, {"height", 1}, {"cells", json::array({json::array({cell})})},
                  {"metadata", {{"schemaVersion", 1}, {"source", "osm+nmt"},
                                {"crs", "EPSG:2180"}, {"cellSizeMeters", 1}}}};
    try {
        write(valid);
        auto map = JsonMapImporter::load(path.string());
        if (map.getCell(0, 0).elevation != 120 || *map.getCell(0, 0).groundElevation != 100 ||
            map.getCell(0, 0).buildingId != "way/1" || map.getMetadata() != valid["metadata"])
            throw std::runtime_error("Imported data was not preserved");
        auto reject = [&](const std::function<void(json&)>& mutate) {
            auto invalid = valid;
            mutate(invalid);
            write(invalid);
            bool rejected = false;
            try { JsonMapImporter::load(path.string()); }
            catch (const std::exception&) { rejected = true; }
            if (!rejected) throw std::runtime_error("Invalid map was accepted");
        };
        reject([](json& j) { j["metadata"]["cellSizeMeters"] = 5; });
        reject([](json& j) { j["width"] = -1; });
        reject([](json& j) { j["width"] = 1000001; });
        reject([](json& j) { j["cells"] = json::array(); });
        reject([](json& j) { j["cells"][0][0]["terrain"] = "unknown"; });
        reject([](json& j) { j["cells"][0][0]["groundElevation"] = 130; });
        reject([](json& j) { j["cells"][0][0]["obstacleHeight"] = 15; });
        reject([](json& j) { j["cells"][0][0]["elevation"] = "nan"; });
        reject([](json& j) { j["cells"][0][0]["concealment"] = 2; });
        Map visibility(3, 1);
        for (int x = 0; x < 3; ++x) {
            visibility.getCell(x, 0).elevation = 100;
            visibility.getCell(x, 0).groundElevation = 100;
        }
        visibility.getCell(1, 0).terrain = TerrainType::Building;
        visibility.getCell(1, 0).elevation = 105;
        ThreatMap threats;
        threats.addRadar(RadarStation(1, 0, 0, 10, 1, 10));
        threats.calculateThreats(visibility, 10);
        if (visibility.getCell(2, 0).threatLevel <= 0)
            throw std::runtime_error("Imported building height counted twice in LOS");
        visibility.getCell(1, 0).elevation = 120;
        threats.calculateThreats(visibility, 10);
        if (visibility.getCell(2, 0).threatLevel != 0)
            throw std::runtime_error("Imported building does not block LOS");
        std::filesystem::remove(path);
        std::cout << "Map import validation passed\n";
    } catch (const std::exception& error) {
        std::filesystem::remove(path);
        std::cerr << error.what() << '\n';
        return 1;
    }
}
