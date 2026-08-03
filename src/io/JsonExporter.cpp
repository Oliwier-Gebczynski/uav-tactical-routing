#include "JsonExporter.h"
#include <fstream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

void JsonExporter::save(const Map& map, const std::string& filename){
    json output;

    output["width"] = map.getWidth();
    output["height"] = map.getHeight();

    for(int y = 0; y < map.getHeight(); y++){
        for(int x = 0; x < map.getWidth(); x++){
            const Cell& cell = map.getCell(x,y);

            json c;

            c["terrain"] = TerrainTypeToString(cell.terrain);
            c["elevation"] = cell.elevation;
            c["obstacle"] = cell.obstacle;
            c["concealment"] = cell.concealment;

            output["cells"][y][x] = c;
        }
    }

    std::ofstream file(filename);

    file << output.dump(4);
}