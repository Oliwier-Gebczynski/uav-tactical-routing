#pragma once                                                
                                                                
#include "../../Map.h"                                         
#include <random>                                           
                                                                
class IMap {                                            
    public:                                                     
        virtual ~IMap() = default;                          
        virtual void generate(Map& map, std::mt19937& rng) = 0; 
};