#include "TestMapGenerator.h"
#include <cmath>
#include <algorithm>

void TestMapGenerator::generateFlatMap(Map& map, float groundElevation) {
    int w = map.getWidth();
    int h = map.getHeight();

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            Cell& c = map.getCell(x, y);
            c.terrain = TerrainType::Grass;
            c.elevation = groundElevation;
            c.concealment = 0.1f;
            c.obstacle = false;
            c.threatLevel = 0.0f;
        }
    }
}

void TestMapGenerator::generateRidgeMap(Map& map, float baseElevation, float ridgeHeight) {
    int w = map.getWidth();
    int h = map.getHeight();
    float ridgeCenterX = w / 2.0f;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            Cell& c = map.getCell(x, y);
            float dx = x - ridgeCenterX;

            float ridgeContribution = ridgeHeight * std::exp(-(dx * dx) / (2.0f * 4.0f * 4.0f));

            c.elevation = baseElevation + ridgeContribution;
            c.threatLevel = 0.0f;
            c.obstacle = false;

            if (ridgeContribution > 15.0f) {
                c.terrain = TerrainType::Forest;
                c.concealment = 0.6f;
            } else {
                c.terrain = TerrainType::Grass;
                c.concealment = 0.1f;
            }
        }
    }
}

void TestMapGenerator::generateCanyonMap(Map& map, float baseElevation, float peakHeight, float canyonDepth) {
    int w = map.getWidth();
    int h = map.getHeight();

    float peak1X = w * 0.25f;
    float peak1Y = h * 0.50f;
    float peak2X = w * 0.75f;
    float peak2Y = h * 0.50f;
    float canyonX = w * 0.50f;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            Cell& c = map.getCell(x, y);

            float distSq1 = std::pow(x - peak1X, 2) + std::pow(y - peak1Y, 2);
            float peak1 = peakHeight * std::exp(-distSq1 / (2.0f * 7.0f * 7.0f));

            float distSq2 = std::pow(x - peak2X, 2) + std::pow(y - peak2Y, 2);
            float peak2 = peakHeight * std::exp(-distSq2 / (2.0f * 7.0f * 7.0f));

            float dxCanyon = x - canyonX;
            float canyonCut = canyonDepth * std::exp(-(dxCanyon * dxCanyon) / (2.0f * 4.0f * 4.0f));

            float finalElevation = std::max(0.0f, baseElevation + peak1 + peak2 - canyonCut);
            c.elevation = finalElevation;
            c.threatLevel = 0.0f;
            c.obstacle = false;

            if (finalElevation < 3.5f) {
                c.terrain = TerrainType::Water;
                c.concealment = 0.0f;
            } else if (peak1 > 10.0f || peak2 > 10.0f) {
                c.terrain = TerrainType::Forest;
                c.concealment = 0.5f;
            } else {
                c.terrain = TerrainType::Grass;
                c.concealment = 0.1f;
            }
        }
    }
}
