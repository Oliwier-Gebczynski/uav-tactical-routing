#pragma once                                                
                                                                
#include "IMap.h"                                       
                                                                
class RoadTerrain : public IMap {                          
    public:                                                     
        void generate(Map& map, std::mt19937& rng) override;                                                        
        static void placeRoadSegment(Map& map, int x0, int y0, int x1, int y1);                                              
}; 