#include <iostream>                                                                  
#include <random>                                                                    
#include "map/Map.h"                                                                 
#include "map/generators/MapGenerator.h"                                             
#include "map/threats/ThreatMap.h"                                                       
#include "io/JsonExporter.h"                                                         
                                                                                         
int main() {                                                                         
    int seed = 67;                                                                   
    std::mt19937 rng(seed);                                                          
                                                                                         
    std::cout << "1. Tworzenie siatki mapy 100x100..." << std::endl;                 
    Map map(100, 100);                                                               
                                                                                         
    std::cout << "2. Generowanie realistycznego terenu..." << std::endl;             
    MapGenerator::generateProceduralMap(map, seed);                                  
                                                                                         
    std::cout << "3. Rozmieszczanie radarów i obliczanie stref zagrożenia (Line-of-Sight)..." << std::endl;                                                               
    ThreatMap threatMap;                                                             
          
    threatMap.generateProceduralRadars(map, 3, 30.0f, rng);                                      
    threatMap.calculateThreats(map, 10.0f);                                          
                                                                                         
    std::cout << "4. Eksport mapy do JSON..." << std::endl;                          
    JsonExporter::save(map, "data/maps/perlin_full_test_map.json", threatMap.getRadars());                                                                          
                                                                                         
    std::cout << "Gotowe! Wynik zapisano w data/maps/perlin_full_test_map.json" << std::endl;                                                                             
    return 0;                                                                        
}