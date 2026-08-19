#pragma once                                                
                                                                
#include "IMap.h"                                       
                                                                
class BuildingTerrain : public IMap {                      
    public:                                                     
        void generate(Map& map, std::mt19937& rng) override;                                                          
        static void placeBuilding(Map& map, int startX, int startY, int width, int height, float buildingHeight);         
};