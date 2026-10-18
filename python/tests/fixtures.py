"""Shared map and scenario fixtures for Python tests."""
from uav_routing.scenarios.model import new_state, optimizer_profile


def fixture():
    cell = {"terrain": "grass", "elevation": 100.0, "groundElevation": 100.0, "obstacleHeight": 0.0,
            "obstacle": False, "landCoverKnown": True, "concealment": 0.1, "threatLevel": 0.0}
    return {"width": 24, "height": 24, "cells": [[dict(cell) for _ in range(24)] for _ in range(24)],
            "metadata": {"schemaVersion": 1, "source": "osm+nmt", "crs": "EPSG:2180", "cellSizeMeters": 1.0}}


def state_fixture():
    state = new_state(24)
    state["name"] = "Powtarzalny test"
    state["start"] = {"x": 2, "y": 2, "name": "Start"}
    state["checkpoints"] = [{"x": 5, "y": 19, "name": "C1"}]
    state["end"] = {"x": 21, "y": 21, "name": "Koniec"}
    state["radars"] = [{"id": 1, "x": 12, "y": 12, "range": 8, "antennaHeight": 10, "baseThreat": .8}]
    state["optimizer"] = optimizer_profile("Szybki", 24)
    state["optimizer"].update(initialTemperature=20, minTemperature=5, coolingRate=.5, iterationsPerTemp=2)
    state["weights"]["threatWeight"] = 123.0
    return state


