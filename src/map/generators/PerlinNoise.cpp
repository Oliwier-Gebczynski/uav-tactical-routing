#include "PerlinNoise.h"

#include <cmath>
#include <numeric>
#include <random>
#include <algorithm>

float PerlinNoise::fade(float t){
    return t * t * t * (t * (t * 6.0f - 15.0f) + 10.0f);
}

float PerlinNoise::lerp(float t, float a, float b){
    return a + t * (b - a);
}

float PerlinNoise::grad(int hash, float x, float y){
    int h = hash & 3;
    float u = (h < 2) ? x : y;
    float v = (h < 2) ? y : x;
    return ((h & 1) == 0 ? u : -u) + ((h & 2) == 0 ? v : -v);
}

PerlinNoise::PerlinNoise(unsigned int seed){
    p.resize(256);
    std::iota(p.begin(), p.end(), 0);

    std::default_random_engine engine(seed);
    std::shuffle(p.begin(), p.end(), engine);

    p.insert(p.end(), p.begin(), p.end());
}

float PerlinNoise::noise(float x, float y) const{
    int X = static_cast<int>(std::floor(x)) & 255;
    int Y = static_cast<int>(std::floor(y)) & 255;

    x -= std::floor(x);
    y -= std::floor(y);

    float u = fade(x);
    float v = fade(y);

    int A = p[X] + Y;
    int B = p[X + 1] + Y;

    float res = lerp(v, lerp(u, grad(p[A], x, y), grad(p[B], x - 1.0f, y)), lerp(u, grad(p[A + 1], x, y - 1.0f), grad(p[B + 1], x - 1.0f, y - 1.0f)));

    return (res + 1.0f) * 0.5f;
}

float PerlinNoise::octaveNoise(float x, float y, int octaves, float persistence) const {
    float total = 0.0f;
    float frequency = 1.0f;
    float amplitude = 1.0f;
    float maxValue = 0.0f;

    for (int i = 0; i < octaves; ++i) {
        total += noise(x * frequency, y * frequency) * amplitude;
        maxValue += amplitude;
        amplitude *= persistence;
        frequency *= 2.0f;
    }

    return total / maxValue;
}