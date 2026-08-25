#pragma once

#include <string>

enum class WaypointType {
    Start,          // Baza startowa / Start misji
    Reconnaissance, // Cel rozpoznania / Obiekt zainteresowania
    Transit,        // Punkt nawigacyjny / korytarz przelotowy
    Return          // Punkt powrotu / Lądowisko
};

inline std::string WaypointTypeToString(WaypointType type) {
    switch (type) {
        case WaypointType::Start:
            return "start";
        case WaypointType::Reconnaissance:
            return "reconnaissance";
        case WaypointType::Transit:
            return "transit";
        case WaypointType::Return:
            return "return";
    }
    return "unknown";
}

struct Point3D {
    float x;
    float y;
    float z; // Wysokość bezwzględna (m n.p.m.)

    Point3D() : x(0.0f), y(0.0f), z(0.0f) {}
    Point3D(float x, float y, float z = 0.0f) : x(x), y(y), z(z) {}

    bool operator==(const Point3D& other) const {
        return static_cast<int>(x) == static_cast<int>(other.x) &&
               static_cast<int>(y) == static_cast<int>(other.y);
    }
};

struct Waypoint {
    int id;
    float x;
    float y;
    float altitudeAGL; // Wysokość nad gruntem (Above Ground Level, np. 10m)
    WaypointType type;
    std::string name;

    Waypoint(int id, float x, float y, float altitudeAGL = 10.0f,
             WaypointType type = WaypointType::Reconnaissance, const std::string& name = "")
        : id(id), x(x), y(y), altitudeAGL(altitudeAGL), type(type), name(name) {}
};
