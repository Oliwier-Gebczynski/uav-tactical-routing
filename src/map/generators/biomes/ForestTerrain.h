#pragma once

#include "IMap.h"
#include "../PerlinNoise.h"

class ForestTerrain : public IMap {
    private:
        PerlinNoise noise;
        float scale;
        float forestThreshold;

    public:
        explicit ForestTerrain(int seed, float scale = 0.035f, float forestThreshold = 0.56f);
        void generate(Map& map, std::mt19937& rng) override;
};