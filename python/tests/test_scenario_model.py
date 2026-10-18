import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from uav_routing.scenarios.model import (MapDocument, new_state, scenario_document,
                            state_from_document, validate_state, write_document)

from uav_routing.paths import ROOT
from tests.fixtures import fixture, state_fixture


class ScenarioModelTests(unittest.TestCase):
    def setUp(self):
        self.map = MapDocument(fixture())
        self.state = state_fixture()

    def test_standalone_roundtrip_preserves_map_and_inputs(self):
        result = scenario_document(self.map, self.state)
        self.assertEqual(result["cells"], self.map.data["cells"])
        self.assertEqual([p["type"] for p in result["mission"]["waypoints"]], ["start", "reconnaissance", "return"])
        state = state_from_document(result)
        for key in ("seed", "radars", "optimizer", "weights", "flightAltitude"):
            self.assertEqual(state[key], self.state[key])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            write_document(path, result)
            loaded = MapDocument.load(path)
            self.assertEqual(scenario_document(loaded, state), result)

    def test_draft_can_be_saved_but_not_run(self):
        state = new_state()
        draft = scenario_document(self.map, state, require_mission=False)
        self.assertEqual(draft["mission"]["waypoints"], [])
        with self.assertRaises(ValueError):
            scenario_document(self.map, state)

    def test_snapshot_is_independent_of_later_edits(self):
        snapshot = scenario_document(self.map, self.state)
        self.state["radars"][0]["x"] = 1
        self.state["optimizer"]["initialTemperature"] = 1
        self.assertEqual(snapshot["radars"][0]["x"], 12)
        self.assertEqual(snapshot["scenario"]["optimizer"]["initialTemperature"], 20)
        self.assertIs(snapshot["cells"], self.map.data["cells"])

    def test_invalid_coordinates_and_settings_rejected(self):
        for key, value in (("x", -1), ("y", 24), ("x", float("nan"))):
            state = copy.deepcopy(self.state)
            state["start"][key] = value
            with self.assertRaises(ValueError):
                validate_state(state, 24, 24)
        for key, value in (("seed", 2.5), ("seed", True), ("flightAltitude", float("inf")), ("name", 123)):
            state = copy.deepcopy(self.state)
            state[key] = value
            with self.assertRaises(ValueError):
                validate_state(state, 24, 24)

    def test_duplicate_radars_and_noninteger_radar_positions_rejected(self):
        state = copy.deepcopy(self.state)
        state["radars"].append(dict(state["radars"][0]))
        with self.assertRaises(ValueError):
            validate_state(state, 24, 24)
        self.state["radars"][0]["x"] = 1.5
        with self.assertRaises(ValueError):
            validate_state(self.state, 24, 24)

    def test_result_reopens_original_mission_not_optimized_transit_points(self):
        document = scenario_document(self.map, self.state)
        original = copy.deepcopy(document["mission"])
        document["inputMission"] = original
        document["mission"]["waypoints"] = [{"type": "transit", "x": 10, "y": 10}]
        state = state_from_document(document)
        self.assertEqual(state["start"]["x"], 2)
        self.assertEqual(len(state["checkpoints"]), 1)

    def test_invalid_map_is_rejected(self):
        for key, value in (("width", -1), ("height", 23), ("width", True)):
            data = fixture()
            data[key] = value
            with self.assertRaises(ValueError):
                MapDocument(data)
        data = fixture()
        data["cells"][0][0]["elevation"] = float("nan")
        with self.assertRaises(ValueError):
            MapDocument(data)


class PlannerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable = Path(os.environ.get("UAV_PLANNER", str(ROOT / "build/UAVPlanner")))
        if not cls.executable.is_file():
            raise unittest.SkipTest("Build UAVPlanner before running integration tests")

    def run_planner(self, source, target):
        return subprocess.run([str(self.executable), "--scenario", str(source), "--output", str(target)],
                              capture_output=True, text=True, timeout=45)

    def test_repeatable_simulation_and_result_replay(self):
        document = scenario_document(MapDocument(fixture()), state_fixture())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_document(root / "scenario.json", document)
            outputs = []
            for name in ("one", "two"):
                path = root / (name + ".json")
                run = self.run_planner(source, path)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                outputs.append(json.loads(path.read_text()))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0]["scenario"], document["scenario"])
            self.assertEqual(outputs[0]["inputMission"], document["mission"])
            self.assertEqual(outputs[0]["pathCost"]["totalCost"], outputs[0]["comparison"]["sa_ls"]["totalCost"])
            self.assertEqual(outputs[0]["pathCost"]["threatRisk"], outputs[0]["comparison"]["sa_ls"]["threatRisk"])
            for key in ("pure_ls", "pure_sa", "sa_ls"):
                points = outputs[0]["comparison"][key]["waypoints"]
                self.assertTrue(any(p["x"] == 5 and p["y"] == 19 and p["type"] == "reconnaissance" for p in points))
            run = self.run_planner(root / "one.json", root / "replay.json")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(outputs[0], json.loads((root / "replay.json").read_text()))

    def test_invalid_scenarios_fail_before_simulation(self):
        valid = scenario_document(MapDocument(fixture()), state_fixture())
        variants = []
        invalid = copy.deepcopy(valid)
        invalid["radars"][0]["x"] = 999
        variants.append(invalid)
        invalid = copy.deepcopy(valid)
        invalid["scenario"]["optimizer"]["coolingRate"] = 1
        variants.append(invalid)
        invalid = copy.deepcopy(valid)
        invalid["mission"]["waypoints"][0]["type"] = "return"
        variants.append(invalid)
        invalid = copy.deepcopy(valid)
        invalid["mission"]["waypoints"][1]["altitudeAGL"] = 25
        variants.append(invalid)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for document in variants:
                source = write_document(root / "invalid.json", document)
                run = self.run_planner(source, root / "result.json")
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse((root / "result.json").exists())

    def test_legacy_procedural_maps_can_be_simulated(self):
        data = fixture()
        del data["metadata"]
        for row in data["cells"]:
            for cell in row:
                for key in ("groundElevation", "obstacleHeight", "landCoverKnown"):
                    del cell[key]
        document = scenario_document(MapDocument(data), state_fixture())
        with tempfile.TemporaryDirectory() as directory:
            source = write_document(Path(directory) / "scenario.json", document)
            run = self.run_planner(source, Path(directory) / "result.json")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
