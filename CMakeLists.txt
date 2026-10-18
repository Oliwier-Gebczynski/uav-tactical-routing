cmake_minimum_required(VERSION 3.20)

project(UAVTrajectoryPlanner)
set(CMAKE_CXX_STANDARD 20)
find_package(nlohmann_json REQUIRED)

add_executable(
    UAVPlanner
    src/main.cpp
    src/map/Map.cpp
    src/io/JsonExporter.cpp
    src/io/JsonMapImporter.cpp
    src/io/ScenarioRunner.cpp
    src/map/generators/PerlinNoise.cpp
    src/map/generators/MapGenerator.cpp
    src/map/generators/biomes/BaseTerrain.cpp
    src/map/generators/biomes/ForestTerrain.cpp
    src/map/generators/biomes/RoadTerrain.cpp
    src/map/generators/biomes/BuildingTerrain.cpp
    src/map/generators/TestMapGenerator.cpp
    src/map/threats/ThreatMap.cpp
    src/routing/Path.cpp
    src/routing/Mission.cpp
    src/planner/CostEvaluator.cpp
    src/planner/LocalSearch.cpp
    src/planner/SimulatedAnnealing.cpp
)

target_include_directories(
    UAVPlanner
    PRIVATE
    src
)

target_link_libraries(
    UAVPlanner
    PRIVATE
    nlohmann_json::nlohmann_json
)

include(CTest)
if(BUILD_TESTING)
    add_executable(JsonMapImporterTest tests/JsonMapImporterTest.cpp src/io/JsonMapImporter.cpp src/map/Map.cpp src/map/threats/ThreatMap.cpp)
    target_include_directories(JsonMapImporterTest PRIVATE src)
    target_link_libraries(JsonMapImporterTest PRIVATE nlohmann_json::nlohmann_json)
    add_test(NAME JsonMapImporter COMMAND JsonMapImporterTest)
endif()
