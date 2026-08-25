#include "ThreatMap.h"
#include <cmath>
#include <algorithm>

void ThreatMap::addRadar(const RadarStation& radar){
    radars.push_back(radar);
}

void ThreatMap::clearRadars(){
    radars.clear();
}

const std::vector<RadarStation>& ThreatMap::getRadars() const{
    return radars;
}

bool ThreatMap::hasLineOfSight(const Map& map, const RadarStation& radar, int targetX, int targetY, float uavAltitudeAboveGround) const{
    if(!map.isInside(radar.x, radar.y) || !map.isInside(targetX, targetY)){
        return false;
    }

    float radarAlt = map.getCell(radar.x, radar.y).elevation + radar.antennaHeight;

    float targetAlt = map.getCell(targetX, targetY).elevation + uavAltitudeAboveGround;

    float dx = static_cast<float>(targetX - radar.x);
    float dy = static_cast<float>(targetY - radar.y);
    float distance = std::sqrt(dx * dx + dy * dy);

    if(distance < 1.0f){
        return true;
    }

    int steps = static_cast<int>(std::ceil(distance * 2.0f));

    for(int step = 1; step < steps; ++step){
        float t = static_cast<float>(step) / static_cast<float>(steps);

        int sampleX = static_cast<int>(std::round(radar.x + t * dx));
        int sampleY = static_cast<int>(std::round(radar.y + t * dy));

        if (!map.isInside(sampleX, sampleY)) continue;

        // Pomiń punkt startowy (radar) oraz cel (UAV) - sprawdzamy tylko przeszkody pośrednie
        if ((sampleX == radar.x && sampleY == radar.y) || (sampleX == targetX && sampleY == targetY)) {
            continue;
        }

        float rayHeight = radarAlt + t * (targetAlt - radarAlt);

        const Cell& sampleCell = map.getCell(sampleX, sampleY);
        float effectiveTerrainHeight = sampleCell.elevation + getTerrainFeatureHeight(sampleCell.terrain);

        if (effectiveTerrainHeight > rayHeight) {
            return false;
        }
    }

    return true;
}

void ThreatMap::generateProceduralRadars(const Map& map, int count, float minDistanceBetweenRadars, std::mt19937& rng) {                                         
    int w = map.getWidth();                                                          
    int h = map.getHeight();                                                         
                 
    struct Candidate {                                                               
        int x, y;                                                                    
        float elevation;                                                             
    };                                                                               
    std::vector<Candidate> candidates;                                               
                                                                                         
    for (int y = 2; y < h - 2; ++y) {                                                
        for (int x = 2; x < w - 2; ++x) {                                            
            const Cell& c = map.getCell(x, y);                                       
            if (c.terrain != TerrainType::Water && c.terrain != TerrainType::Road) { 
                candidates.push_back({x, y, c.elevation});                           
            }                                                                        
        }                                                                            
    }                                                                                
                                                                                                                                                                       
    std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {                                                                        
        return a.elevation > b.elevation;                                            
    });                                                                              
                       
    int idCounter = 1;                                                               
    for (const auto& cand : candidates) {                                            
        if (static_cast<int>(radars.size()) >= count) break;                         
                                                                                         
        bool tooClose = false;                                                       
        for (const auto& r : radars) {                                               
            float dist = std::sqrt(std::pow(cand.x - r.x, 2) + std::pow(cand.y - r.y, 2));                                                                                   
            if (dist < minDistanceBetweenRadars) {                                   
                tooClose = true;                                                     
                break;                                                               
            }                                                                        
        }                                                                            
                                                                                         
        if (!tooClose) {                                                                                        
            radars.emplace_back(idCounter++, cand.x, cand.y, 28.0f, 1.0f, 15.0f);     
        }                                                                            
    }                                                                                
}                                                                                    
                                                                                         
void ThreatMap::calculateThreats(Map& map, float uavFlightAltitude) {                
    int w = map.getWidth();                                                          
    int h = map.getHeight();                                                         
                                  
    for (int y = 0; y < h; ++y) {                                                    
        for (int x = 0; x < w; ++x) {                                                
            map.getCell(x, y).threatLevel = 0.0f;                                    
        }                                                                            
    }                                                                                
                                             
    for (const auto& radar : radars) {                                               
        int minX = std::max(0, static_cast<int>(radar.x - radar.range));             
        int maxX = std::min(w - 1, static_cast<int>(radar.x + radar.range));         
        int minY = std::max(0, static_cast<int>(radar.y - radar.range));             
        int maxY = std::min(h - 1, static_cast<int>(radar.y + radar.range));         
                                                                                         
        for (int y = minY; y <= maxY; ++y) {                                         
            for (int x = minX; x <= maxX; ++x) {                                     
                float dist = std::sqrt(std::pow(x - radar.x, 2) + std::pow(y - radar.y, 2));                                                                                
                                                                                         
                if (dist <= radar.range) {                                                               
                    if (hasLineOfSight(map, radar, x, y, uavFlightAltitude)) {                           
                        float factor = (1.0f - (dist / radar.range));                
                        float threat = radar.baseThreat * factor * factor;           
                                                                                         
                        Cell& cell = map.getCell(x, y);                                                 
                        cell.threatLevel = std::min(1.0f, cell.threatLevel + threat);
                    }                                                                
                }                                                                    
            }                                                                        
        }                                                                            
    }                                                                                
}