#include "map/Map.h"
#include "io/JsonExporter.h"

int main(){

    Map map(100,100);

    map.getCell(20,20).terrain = TerrainType::Forest;
    map.getCell(20,20).elevation = 120.5;
    map.getCell(20,20).concealment = 0.8;

    map.getCell(80,80).terrain = TerrainType::Road;
    map.getCell(80,80).elevation = 120.5;
    map.getCell(80,80).concealment = 0.8;

    JsonExporter::save(
        map,
        "data/maps/test_map.json"
    );

    return 0;
}