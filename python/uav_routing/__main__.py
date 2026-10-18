"""Command dispatch with lazy imports for standalone tools."""
import argparse
from importlib import import_module
import runpy
import sys


COMMANDS = {
    "gui": ("uav_routing.gui.mission_control", "main"),
    "import-map": ("uav_routing.maps.osm_importer", "main"),
    "view": ("uav_routing.visualization.terrain_viewer", None),
    "dashboard": ("uav_routing.visualization.tactical_viewer", None),
    "benchmark": ("uav_routing.visualization.benchmark_comparator", None),
}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        command = sys.argv.pop(1)
    else:
        parser = argparse.ArgumentParser(description="UAV routing tools. Omit the command to open the GUI.")
        parser.add_argument("command", nargs="?", choices=COMMANDS, default="gui",
                            help="gui, import-map, view, dashboard or benchmark")
        command = parser.parse_args().command
    module, entry = COMMANDS[command]
    if entry:
        getattr(import_module(module), entry)()
    else:
        runpy.run_module(module, run_name="__main__")


if __name__ == "__main__":
    main()
