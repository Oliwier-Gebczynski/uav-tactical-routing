#include "MapGenerator.h"                                   
#include "./biomes/BaseTerrain.h"                                
#include "./biomes/ForestTerrain.h"                                     
#include "./biomes/RoadTerrain.h"                                       
#include "./biomes/BuildingTerrain.h"                                   
#include <random>                                           
                                                                
void MapGenerator::addPass(std::unique_ptr<IMap> pass){
    passes.push_back(std::move(pass));                      
}                                                           
                                                                
void MapGenerator::generate(Map& map, int seed){           
    std::mt19937 rng(seed);                                 
    for (auto& pass : passes) {                             
        pass->generate(map, rng);                           
    }                                                       
}                                                           
                                                                
void MapGenerator::generateProceduralMap(Map& map, int seed){                                                             
    MapGenerator generator;                                 
            
    generator.addPass(std::make_unique<BaseTerrain>(seed));             
    generator.addPass(std::make_unique<ForestTerrain>(seed + 100));
    generator.addPass(std::make_unique<RoadTerrain>());        
    generator.addPass(std::make_unique<BuildingTerrain>());    

    generator.generate(map, seed);
}