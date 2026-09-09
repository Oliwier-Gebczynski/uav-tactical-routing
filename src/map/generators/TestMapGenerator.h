#pragma once

#include "../Map.h"

class TestMapGenerator {
public:

    static void generateFlatMap(Map& map, float groundElevation = 5.0f);

    static void generateRidgeMap(Map& map, float baseElevation = 5.0f, float ridgeHeight = 45.0f);

    static void generateCanyonMap(Map& map, float baseElevation = 25.0f, float peakHeight = 35.0f, float canyonDepth = 23.0f);
};
