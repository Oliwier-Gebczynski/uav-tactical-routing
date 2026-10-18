"""Portable scenario documents and validation, independent of the GUI."""
import copy
import json
import math
from pathlib import Path

import numpy as np

TERRAIN = {"water": 0, "grass": 1, "forest": 2, "road": 3, "building": 4}
PROFILES = {
    "Szybki": {"initialTemperature": 120.0, "minTemperature": 1.0, "coolingRate": 0.93, "iterationsPerTemp": 6},
    "Standard": {"initialTemperature": 800.0, "minTemperature": 0.05, "coolingRate": 0.99, "iterationsPerTemp": 15},
    "Dokładny": {"initialTemperature": 800.0, "minTemperature": 0.05, "coolingRate": 0.995, "iterationsPerTemp": 25},
}


def optimizer_profile(name="Standard", size=200):
    return dict(PROFILES[name], maxPerturbation=max(12.0, size * 0.08), maxWaypoints=100,
                enableLocalSearch=True, enablePeriodicLocalSearch=True, localSearchInterval=80,
                probPerturb=0.70, probInsert=0.15, probDelete=0.15)


class MapDocument:
    def __init__(self, data, path=None):
        self.data = data
        self.path = Path(path).resolve() if path else None
        self.width, self.height = data.get("width"), data.get("height")
        if (type(self.width) is not int or type(self.height) is not int or self.width < 2 or self.height < 2
                or self.width * self.height > 1_000_000):
            raise ValueError("Mapa musi mieć co najmniej 2 × 2 i najwyżej milion komórek.")
        rows = data.get("cells", [])
        if len(rows) != self.height or any(not isinstance(row, list) or len(row) != self.width for row in rows):
            raise ValueError("Nieprawidłowy rozmiar siatki mapy.")
        metadata = data.get("metadata", {})
        if metadata and (metadata.get("cellSizeMeters") != 1 or metadata.get("source") != "osm+nmt"
                         or metadata.get("crs") != "EPSG:2180" or metadata.get("schemaVersion") != 1):
            raise ValueError("Obsługiwane są mapy OSM+NMT w EPSG:2180, 1 m na komórkę, lub mapy proceduralne.")
        try:
            self.terrain = np.array([[TERRAIN[c["terrain"]] for c in row] for row in rows], dtype=np.uint8)
            self.surface = np.array([[c["elevation"] for c in row] for row in rows], dtype=np.float32)
            self.ground = np.array([[c.get("groundElevation", c["elevation"]) for c in row] for row in rows], dtype=np.float32)
            self.threat = np.array([[c.get("threatLevel", 0.0) for c in row] for row in rows], dtype=np.float32)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Nieprawidłowy typ terenu lub wysokość w mapie.") from error
        if any(not np.isfinite(array).all() for array in (self.surface, self.ground, self.threat)):
            raise ValueError("Mapa zawiera niepoprawne wartości liczbowe.")
        if (self.surface < self.ground - 0.01).any() or (self.threat < 0).any() or (self.threat > 1).any():
            raise ValueError("Nieprawidłowa wysokość przeszkód lub poziom zagrożenia.")
        self.has_ground = bool(rows[0][0].get("groundElevation") is not None)
        validate_state(state_from_document(data), self.width, self.height, require_mission=False)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as file:
            return cls(json.load(file), path)


def new_state(size=200):
    return {"name": "Nowy scenariusz", "seed": 42, "flightAltitude": 10.0, "radars": [],
            "start": None, "checkpoints": [], "end": None, "optimizer": optimizer_profile(size=size),
            "weights": {"distanceWeight": 1.0, "threatWeight": 50.0, "obstacleWeight": 10000.0,
                        "baseCollisionPenalty": 100.0, "altitudeSafetyMargin": 0.0}}


def state_from_document(document):
    state = new_state(max(document["width"], document["height"]))
    config = document.get("scenario", {})
    for key in ("name", "seed", "flightAltitude"):
        if key in config:
            state[key] = copy.deepcopy(config[key])
    for key in ("optimizer", "weights"):
        if key in config:
            state[key].update(copy.deepcopy(config[key]))
    state["radars"] = copy.deepcopy(document.get("radars", []))
    mission = document.get("inputMission", document.get("mission", {}))
    if not document.get("inputMission") and document.get("comparison", {}).get("baseline"):
        mission = {"waypoints": document["comparison"]["baseline"].get("waypoints", [])}
    for point in mission.get("waypoints", []):
        kind = point.get("type")
        if kind == "start":
            state["start"] = copy.deepcopy(point)
        elif kind == "return":
            state["end"] = copy.deepcopy(point)
        elif kind == "reconnaissance":
            state["checkpoints"].append(copy.deepcopy(point))
    return state


def finite(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Niepoprawna wartość: {name} ({low}–{high}).")


def validate_state(state, width, height, require_mission=True):
    if not isinstance(state["name"], str) or not 1 <= len(state["name"]) <= 200:
        raise ValueError("Nazwa scenariusza musi mieć od 1 do 200 znaków.")
    finite(state["seed"], "seed", 0, 2147483647)
    if type(state["seed"]) is not int:
        raise ValueError("Seed musi być liczbą całkowitą.")
    finite(state["flightAltitude"], "wysokość lotu", 0.1, 1000)
    if require_mission and (state["start"] is None or state["end"] is None):
        raise ValueError("Ustaw start i koniec lotu na mapie.")
    if len(state["radars"]) > 100 or len(state["checkpoints"]) > 98:
        raise ValueError("Limit: 100 radarów i 98 checkpointów.")
    seen = set()
    for radar in state["radars"]:
        identifier = radar.get("id")
        if type(identifier) is not int or not 1 <= identifier <= 1000000 or identifier in seen:
            raise ValueError("Radary muszą mieć unikalne dodatnie identyfikatory.")
        seen.add(identifier)
        for key, upper in (("x", width - 1), ("y", height - 1)):
            finite(radar.get(key), f"radar {key}", 0, upper)
            if type(radar[key]) is not int:
                raise ValueError("Pozycja radaru musi wskazywać całkowity indeks komórki.")
        finite(radar.get("range"), "zasięg radaru", 1, 2000)
        finite(radar.get("baseThreat"), "siła radaru", 0, 1)
        finite(radar.get("antennaHeight"), "wysokość anteny", 0, 1000)
    points = [state["start"], *state["checkpoints"], state["end"]]
    for point in points:
        if point is not None:
            finite(point.get("x"), "punkt x", 0, width - 1)
            finite(point.get("y"), "punkt y", 0, height - 1)
    optimizer = state["optimizer"]
    for key, low, high in (("initialTemperature", 0.1, 10000), ("minTemperature", 0.001, 10000),
                           ("coolingRate", 0.1, 0.9999), ("iterationsPerTemp", 1, 1000),
                           ("maxPerturbation", 0.1, 1000), ("maxWaypoints", 2, 200),
                           ("localSearchInterval", 1, 100000)):
        finite(optimizer.get(key), key, low, high)
    if optimizer["minTemperature"] >= optimizer["initialTemperature"]:
        raise ValueError("Temperatura minimalna musi być niższa od początkowej.")
    for key in ("iterationsPerTemp", "maxWaypoints", "localSearchInterval"):
        if type(optimizer[key]) is not int:
            raise ValueError(f"{key} musi być liczbą całkowitą.")
    if optimizer["maxWaypoints"] < sum(p is not None for p in points):
        raise ValueError("Limit punktów optymalizatora jest mniejszy od liczby punktów misji.")
    for key in ("enableLocalSearch", "enablePeriodicLocalSearch"):
        if type(optimizer.get(key)) is not bool:
            raise ValueError(f"Niepoprawny przełącznik: {key}.")
    for key in ("probPerturb", "probInsert", "probDelete"):
        finite(optimizer.get(key), key, 0, 1)
    if abs(sum(optimizer[k] for k in ("probPerturb", "probInsert", "probDelete")) - 1) > 0.0001:
        raise ValueError("Prawdopodobieństwa ruchów muszą sumować się do 1.")
    for key in ("distanceWeight", "threatWeight", "obstacleWeight", "baseCollisionPenalty", "altitudeSafetyMargin"):
        finite(state["weights"].get(key), key, 0, 1000 if key == "altitudeSafetyMargin" else 1000000)


def scenario_document(map_document, state, require_mission=True):
    validate_state(state, map_document.width, map_document.height, require_mission)
    # Share the immutable terrain while editing. No million-cell deepcopy.
    result = {key: map_document.data[key] for key in ("width", "height", "cells", "metadata") if key in map_document.data}
    result["radars"] = copy.deepcopy(state["radars"])
    config = {key: copy.deepcopy(state[key]) for key in ("name", "seed", "flightAltitude", "optimizer", "weights")}
    config["schemaVersion"] = 1
    result["scenario"] = config
    points = []
    for point, kind in [(state["start"], "start"), *[(p, "reconnaissance") for p in state["checkpoints"]], (state["end"], "return")]:
        if point is not None:
            points.append({"id": len(points) + 1, "type": kind, "name": point.get("name", kind),
                           "x": point["x"], "y": point["y"], "altitudeAGL": state["flightAltitude"]})
    result["mission"] = {"waypoints": points}
    return result


def write_document(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(document, file, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path
