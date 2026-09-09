#pragma once

#include "../Map.h"
#include "./biomes/IMap.h"
#include <vector>
#include <memory>

class MapGenerator {
    private:
        std::vector<std::unique_ptr<IMap>> passes;
    public:
        MapGenerator() = default;

        void addPass(std::unique_ptr<IMap> pass);
        void generate(Map& map, int seed);
        static void generateProceduralMap(Map& map, int seed);
};