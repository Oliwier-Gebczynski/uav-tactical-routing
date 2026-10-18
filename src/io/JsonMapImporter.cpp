#include "JsonMapImporter.h"
#include <cmath>
#include <fstream>
#include <stdexcept>

namespace {
float finiteNumber(const nlohmann::json& object, const char* key) {
    const auto& value = object.at(key);
    if (!value.is_number()) throw std::runtime_error(std::string("Expected number: ") + key);
    float result = value.get<float>();
    if (!std::isfinite(result)) throw std::runtime_error(std::string("Non-finite number: ") + key);
    return result;
}

TerrainType terrainType(const std::string& name) {
    if (name == "grass") return TerrainType::Grass;
    if (name == "forest") return TerrainType::Forest;
    if (name == "road") return TerrainType::Road;
    if (name == "building") return TerrainType::Building;
    if (name == "water") return TerrainType::Water;
    throw std::runtime_error("Unknown terrain type: " + name);
}
}

Map JsonMapImporter::load(const std::string& filename) {
    std::ifstream file(filename);
    if (!file) throw std::runtime_error("Cannot open map: " + filename);
    const auto data = nlohmann::json::parse(file);
    return fromJson(data);
}

Map JsonMapImporter::fromJson(const nlohmann::json& data, bool allowLegacy) {
    if (!data.at("width").is_number_integer() || !data.at("height").is_number_integer())
        throw std::runtime_error("Map dimensions must be integers");
    const auto width64 = data.at("width").get<std::int64_t>();
    const auto height64 = data.at("height").get<std::int64_t>();
    if (width64 <= 0 || height64 <= 0 || width64 > 1000000 || height64 > 1000000 || width64 * height64 > 1000000)
        throw std::runtime_error("Map must contain between 1 and 1000000 cells");
    int width = static_cast<int>(width64), height = static_cast<int>(height64);
    const auto metadata = data.value("metadata", nlohmann::json::object());
    const bool imported = !metadata.empty();
    if ((!imported && !allowLegacy) || (imported &&
        (metadata.at("schemaVersion") != 1 || metadata.at("source") != "osm+nmt" ||
        metadata.at("crs") != "EPSG:2180" || finiteNumber(metadata, "cellSizeMeters") != 1.0f)))
        throw std::runtime_error("Expected OSM+NMT schema 1, EPSG:2180, one metre per cell");
    const auto& rows = data.at("cells");
    if (!rows.is_array() || rows.size() != static_cast<size_t>(height))
        throw std::runtime_error("Incorrect cell row count");
    Map map(width, height);
    map.setMetadata(metadata);
    for (int y = 0; y < height; ++y) {
        if (!rows[y].is_array() || rows[y].size() != static_cast<size_t>(width))
            throw std::runtime_error("Incorrect cell column count");
        for (int x = 0; x < width; ++x) {
            const auto& input = rows[y][x];
            auto& cell = map.getCell(x, y);
            cell.terrain = terrainType(input.at("terrain").get<std::string>());
            cell.elevation = finiteNumber(input, "elevation");
            if (imported) {
                cell.groundElevation = finiteNumber(input, "groundElevation");
                const float obstacleHeight = finiteNumber(input, "obstacleHeight");
                if (obstacleHeight < 0 || cell.elevation < *cell.groundElevation ||
                    std::abs(cell.elevation - *cell.groundElevation - obstacleHeight) > 0.01f)
                    throw std::runtime_error("Inconsistent ground and obstacle heights");
            }
            cell.concealment = finiteNumber(input, "concealment");
            cell.threatLevel = finiteNumber(input, "threatLevel");
            if (cell.concealment < 0 || cell.concealment > 1 || cell.threatLevel < 0 || cell.threatLevel > 1)
                throw std::runtime_error("Concealment and threat must be in [0, 1]");
            cell.obstacle = input.at("obstacle").get<bool>();
            cell.landCoverKnown = imported ? input.at("landCoverKnown").get<bool>() : true;
            cell.buildingId = input.value("buildingId", std::string());
        }
    }
    return map;
}
