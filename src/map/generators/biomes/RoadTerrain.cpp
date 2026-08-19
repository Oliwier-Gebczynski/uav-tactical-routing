#include "RoadTerrain.h"                                       
#include <cmath>                                            
#include <cstdlib>                                          
                                                                
void RoadTerrain::placeRoadSegment(Map& map, int x0, int y0, int x1, int y1) {                                             
    int dx = std::abs(x1 - x0);                             
    int dy = -std::abs(y1 - y0);                            
                                                                
    int sx = (x0 < x1) ? 1 : -1;                            
    int sy = (y0 < y1) ? 1 : -1;                            
                                                                
    int err = dx + dy;                                      
                                                                
    while (true) {                                          
        if (map.isInside(x0, y0)) {                         
            Cell& cell = map.getCell(x0, y0);               
            cell.terrain = TerrainType::Road;               
            cell.concealment = 0.0f;                        
        }                                                   
                                                                
        if (x0 == x1 && y0 == y1) break;                    
        int e2 = 2 * err;                                   
        if (e2 >= dy) { err += dy; x0 += sx; }              
        if (e2 <= dx) { err += dx; y0 += sy; }              
    }                                                       
}                                                           
                                                                
void RoadTerrain::generate(Map& map, std::mt19937& rng) {  
    int w = map.getWidth();                                 
    int h = map.getHeight();                                
                                                                
    int mainRoadY = h / 2;                                  
    placeRoadSegment(map, 0, mainRoadY, w - 1, mainRoadY);  
                                                                
    int mainRoadX = w / 3;                                  
    placeRoadSegment(map, mainRoadX, 0, mainRoadX, h - 1);  
                                                                
    placeRoadSegment(map, mainRoadX, mainRoadY + 15, w - 10, h - 10);                                                      
}