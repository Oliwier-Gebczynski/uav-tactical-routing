#include "JsonExporter.h"                                                            
#include <fstream>                                                                   
#include <nlohmann/json.hpp>                                                         
                                                                                         
using json = nlohmann::json;                                                         
                                                                                         
void JsonExporter::save(const Map& map, const std::string& filename, const std::vector<RadarStation>& radars) {                                                   
    json output;                                                                     
                                                                                         
    output["width"] = map.getWidth();                                                
    output["height"] = map.getHeight();                                              
                                                                                         
    for (int y = 0; y < map.getHeight(); y++) {                                      
        for (int x = 0; x < map.getWidth(); x++) {                                   
            const Cell& cell = map.getCell(x, y);                                    
                                                                                         
            json c;                                                                  
            c["terrain"] = TerrainTypeToString(cell.terrain);                        
            c["elevation"] = cell.elevation;                                         
            c["obstacle"] = cell.obstacle;                                           
            c["concealment"] = cell.concealment;                                     
            c["threatLevel"] = cell.threatLevel; // <--- Zapis zagrożenia            
                                                                                         
            output["cells"][y][x] = c;                                               
        }                                                                            
    }                                                                                
                                           
    json radarsJson = json::array();                                                 
    for (const auto& r : radars) {                                                   
        json rj;                                                                     
        rj["id"] = r.id;                                                             
        rj["x"] = r.x;                                                               
        rj["y"] = r.y;                                                               
        rj["range"] = r.range;                                                       
        rj["baseThreat"] = r.baseThreat;                                             
        rj["antennaHeight"] = r.antennaHeight;                                       
        radarsJson.push_back(rj);                                                    
    }                                                                                
    output["radars"] = radarsJson;                                                   
                                                                                         
    std::ofstream file(filename);                                                    
    file << output.dump(4);                                                          
}