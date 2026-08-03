cmake_minimum_required(VERSION 3.20)

project(UAVTrajectoryPlanner)
set(CMAKE_CXX_STANDARD 20)
find_package(nlohmann_json REQUIRED)

add_executable(
    UAVPlanner
    src/main.cpp
    src/map/Map.cpp
    src/io/JsonExporter.cpp
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