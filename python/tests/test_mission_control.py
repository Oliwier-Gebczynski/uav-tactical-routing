import copy
import os
from pathlib import Path
import tempfile
import time
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/uav-test-matplotlib")

from PyQt5 import QtCore, QtWidgets
from uav_routing.gui.mission_control import MissionControl, STYLE, ROOT
from uav_routing.scenarios.model import MapDocument
from tests.fixtures import fixture, state_fixture


class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.window = MissionControl()
        self.window._loaded(MapDocument(fixture()))
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        if self.window.process:
            self.window.cancel_job()
            self.window.process.waitForFinished(3000)
        self.window.dirty = False
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_click_placement_limit_and_undo(self):
        self.window.radar_count.setValue(1)
        self.window.mode.setCurrentIndex(1)
        self.window.map_click(10, 10)
        self.window.map_click(12, 12)
        self.assertEqual(len(self.window.state["radars"]), 1)
        self.window.mode.setCurrentIndex(2)
        self.window.map_click(2, 2)
        self.window.mode.setCurrentIndex(3)
        self.window.map_click(5, 19)
        self.window.mode.setCurrentIndex(4)
        self.window.map_click(21, 21)
        self.assertEqual(len(self.window.state["checkpoints"]), 1)
        self.assertEqual(self.window.state["end"]["x"], 21)
        self.window.undo()
        self.assertIsNone(self.window.state["end"])
        self.assertEqual(len(self.window.state["radars"]), 1)

    def test_remove_and_settings_are_undoable(self):
        self.window.mode.setCurrentIndex(2)
        self.window.map_click(3, 4)
        self.window.mode.setCurrentIndex(5)
        self.window.map_click(3, 4)
        self.assertIsNone(self.window.state["start"])
        self.window.undo()
        self.assertEqual(self.window.state["start"]["x"], 3)
        original = self.window.state["flightAltitude"]
        self.window.altitude.setValue(20)
        self.assertEqual(self.window.state["flightAltitude"], 20)
        self.window.undo()
        self.assertEqual(self.window.state["flightAltitude"], original)

    def test_busy_editor_does_not_mutate_scenario(self):
        self.window.mode.setCurrentIndex(1)
        self.window._set_busy(True)
        before = copy.deepcopy(self.window.state)
        self.window.map_click(10, 10)
        self.assertEqual(self.window.state, before)
        self.assertFalse(self.window.run_button.isEnabled())
        self.window._set_busy(False)

    def test_running_process_can_be_cancelled(self):
        callbacks = []
        self.window._start_process(sys.executable, ["-c", "import time; print('ready', flush=True); time.sleep(60)"],
                                   lambda: callbacks.append(True), "TEST ANULOWANIA")
        QtCore.QTimer.singleShot(100, self.window.cancel_job)
        deadline = time.monotonic() + 5
        while self.window.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertFalse(self.window.busy)
        self.assertEqual(callbacks, [])
        self.assertIn("anulowane", self.window.log.toPlainText())

    def test_layer_switch_and_export(self):
        for index in range(self.window.map_layer.count()):
            self.window.map_layer.setCurrentIndex(index)
            self.app.processEvents()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "preview.png"
            with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(target), "PNG")):
                self.window.export_png(self.window.map_plot)
            self.assertTrue(target.is_file())
            self.assertGreater(target.stat().st_size, 1000)

    def test_simulation_process_populates_all_result_views(self):
        self.window.state = state_fixture()
        self.window._sync_controls()
        with tempfile.TemporaryDirectory() as directory, patch("uav_routing.gui.mission_control.ROOT", Path(directory)):
            temporary_root = Path(directory)
            (temporary_root / "build").mkdir()
            (temporary_root / "build/UAVPlanner").symlink_to(ROOT / "build/UAVPlanner")
            self.window.run_simulation()
            deadline = time.monotonic() + 40
            while (self.window.busy or self.window.worker) and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.app.processEvents()
            self.assertFalse(self.window.busy, self.window.log.toPlainText())
            self.assertIsNotNone(self.window.result, self.window.log.toPlainText())
            self.assertEqual(self.window.tabs.currentIndex(), 2)
            for index in range(self.window.result_view.count()):
                self.window.result_view.setCurrentIndex(index)
                self.app.processEvents()
            self.assertIn("INITIAL", self.window.decisions.toPlainText())


if __name__ == "__main__":
    unittest.main()
