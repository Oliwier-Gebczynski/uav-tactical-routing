#pragma once                                                                         
                                                                                         
#include "../map/Map.h"                                                              
#include "../map/threats/RadarStation.h"                                                 
#include <string>                                                                    
#include <vector>                                                                    
                                                                                         
class JsonExporter {                                                                 
    public:                                                                              
        static void save(const Map& map, const std::string& filename, const std::vector<RadarStation>& radars = {});                                               
}; 