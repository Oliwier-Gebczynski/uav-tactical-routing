#pragma once

#include <vector>

class PerlinNoise {
private:
    std::vector<int> p;

    static float fade(float t);
    static float lerp(float t, float a, float b);
    static float grad(int hash, float x, float y);

public:
    explicit PerlinNoise(unsigned int seed = 1337);

    float noise(float x, float y) const;

    float octaveNoise(float x, float y, int octaves, float persistence = 0.5f) const;
};