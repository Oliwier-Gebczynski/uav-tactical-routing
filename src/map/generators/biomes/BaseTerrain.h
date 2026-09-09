#pragma once
#include "IMap.h"
#include "../PerlinNoise.h"

class BaseTerrain : public IMap{
    private:
        PerlinNoise noise;
        float scale;
        float waterLevel;
        float heightMulti;

    public:
        explicit BaseTerrain(int seed, float scale = 0.025f, float waterLevel = 0.30f, float heightMulti = 35.0f);
        void generate(Map& map, std::mt19937& rng) override;

};