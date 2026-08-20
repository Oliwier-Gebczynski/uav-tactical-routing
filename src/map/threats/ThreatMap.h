#pragma once                                                                         
                                                                                         
#include "../Map.h"                                                              
#include "RadarStation.h"                                                            
#include <vector>                                                                    
#include <random>                                                                    
                                                                                         
class ThreatMap {                                                                    
    private:                                                                             
        std::vector<RadarStation> radars;                                                
                                                                                                                                                  
        bool hasLineOfSight(const Map& map, const RadarStation& radar, int targetX, int targetY, float uavAltitudeAboveGround) const;                                          
                                                                                         
    public:                                                                              
        ThreatMap() = default;                                                           
                                                                                                               
        void addRadar(const RadarStation& radar);                                        
        void clearRadars();                                                              
        const std::vector<RadarStation>& getRadars() const;                              
                                                                                                        
        void generateProceduralRadars(const Map& map, int count, float minDistanceBetweenRadars, std::mt19937& rng);                    
        void calculateThreats(Map& map, float uavFlightAltitude = 10.0f);                
    };