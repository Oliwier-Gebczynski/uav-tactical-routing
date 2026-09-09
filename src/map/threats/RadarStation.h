#pragma once

struct RadarStation {
    int id;
    int x;
    int y;
    float antennaHeight;
    float range;
    float baseThreat;

    RadarStation(int id, int x, int y, float range = 25.0f, float baseThreat = 1.0f, float antennaHeight = 15.0f)
            : id(id), x(x), y(y), antennaHeight(antennaHeight), range(range), baseThreat(baseThreat) {}
};