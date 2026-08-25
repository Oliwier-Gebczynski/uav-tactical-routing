#pragma once

#include "../Map.h"

class TestMapGenerator {
public:
    // 1. Płaski teren - weryfikacja idealnego okręgu zasięgu bez przeszkód
    static void generateFlatMap(Map& map, float groundElevation = 5.0f);

    // 2. Grzbiet górski / Ściana - weryfikacja ostrego cienia radarowego (Radar Shadow)
    static void generateRidgeMap(Map& map, float baseElevation = 5.0f, float ridgeHeight = 45.0f);

    // 3. Kanion i szczyty - porównanie radaru na wzniesieniu vs radaru w wąwozie
    static void generateCanyonMap(Map& map, float baseElevation = 25.0f, float peakHeight = 35.0f, float canyonDepth = 23.0f);
};
