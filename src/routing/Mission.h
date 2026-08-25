#pragma once

#include <vector>
#include <string>
#include "Waypoint.h"
#include "Path.h"
#include "../map/Map.h"

class Mission {
private:
    Waypoint startPoint;
    std::vector<Waypoint> targets;
    Waypoint returnPoint;

public:
    Mission(const Waypoint& start, const Waypoint& returnPoint);

    void addTarget(const Waypoint& target);
    void clearTargets();

    const Waypoint& getStartPoint() const;
    const std::vector<Waypoint>& getTargets() const;
    const Waypoint& getReturnPoint() const;

    // Zwraca uporządkowaną listę wszystkich punktów kontrolnych: Start -> Cele -> Powrót
    std::vector<Waypoint> getAllWaypoints() const;

    // Generuje wstępną, bezpośrednią trasę (kratka po kratce) łączącą wszystkie punkty misji
    Path generateDirectPath(const Map& map) const;
};
