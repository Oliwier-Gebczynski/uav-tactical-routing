import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.transform import from_origin

from uav_routing.maps.osm_importer import (building_height, build_map, fetch_nmt, number,
                            osm_geometry, read_ground, download)


class HeightTests(unittest.TestCase):
    def test_explicit_height_includes_roof(self):
        self.assertEqual(building_height({"height": "12 m", "roof:height": "3", "building:levels": "2"}), (12, "osm:height"))

    def test_units_and_invalid_values(self):
        self.assertAlmostEqual(number("10 ft"), 3.048)
        self.assertAlmostEqual(number("7'4\""), 2.2352)
        for value in ["nan", "inf", "12;15", "-4", "abc"]:
            self.assertIsNone(number(value))

    def test_levels_and_roof(self):
        self.assertEqual(building_height({"building:levels": "4", "roof:height": "3"}), (15, "estimated:levels"))
        self.assertEqual(building_height({"building:levels": "4", "roof:shape": "flat"}), (12, "estimated:levels"))
        self.assertEqual(building_height({"building:levels": "2", "roof:levels": "1"}), (9, "estimated:levels"))

    def test_types_and_unknowns(self):
        self.assertLess(building_height({"building": "house"})[0], building_height({"building": "apartments"})[0])
        self.assertEqual(building_height({"building": "yes"}, 18), (18, "estimated:unknown"))
        self.assertEqual(building_height({"building": "garage", "height": "invalid"}), (3, "estimated:type"))


class RasterTests(unittest.TestCase):
    def setUp(self):
        self.transform = from_origin(500000, 300020, 1, 1)
        self.project = Transformer.from_crs(2180, 4326, always_xy=True)

    def geometry(self, coordinates):
        result = []
        for x, y in coordinates:
            lon, lat = self.project.transform(500000 + x, 300020 - y)
            result.append({"lon": lon, "lat": lat})
        return result

    def way(self, identifier, coordinates, **tags):
        return {"type": "way", "id": identifier, "tags": tags, "geometry": self.geometry(coordinates)}

    def render(self, elements, ground=None):
        return build_map({"elements": elements}, np.full((20, 20), 100, dtype=np.float32) if ground is None else ground,
                         self.transform, {})

    def test_building_has_flat_roof_on_slope(self):
        ground = np.tile(np.arange(20, dtype=np.float32), (20, 1)) + 100
        result = self.render([self.way(1, [(2, 2), (8, 2), (8, 8), (2, 8), (2, 2)], building="house", height="20")], ground)
        cells = [c for row in result["cells"] for c in row if c["terrain"] == "building"]
        self.assertGreater(len(cells), 0)
        self.assertEqual(len({c["elevation"] for c in cells}), 1)
        for cell in cells:
            self.assertAlmostEqual(cell["elevation"], cell["groundElevation"] + cell["obstacleHeight"], places=2)

    def test_building_parts_replace_outline_height(self):
        outline = self.way(1, [(2, 2), (18, 2), (18, 18), (2, 18), (2, 2)], building="yes", height="30")
        part = self.way(2, [(4, 4), (9, 4), (9, 9), (4, 9), (4, 4)], **{"building:part": "yes", "height": "5"})
        result = self.render([outline, part])
        self.assertEqual(result["cells"][6][6]["elevation"], 105)
        self.assertEqual(result["cells"][12][12]["elevation"], 130)
        self.assertEqual(result["cells"][6][6]["buildingId"], "way/2")

    def test_multipolygon_keeps_courtyard(self):
        outer = self.way(1, [(1, 1), (19, 1), (19, 19), (1, 19), (1, 1)], building="yes")
        inner = self.way(2, [(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])
        relation = {"type": "relation", "id": 3, "tags": {"type": "multipolygon", "building": "yes", "height": "10"},
                    "members": [{"type": "way", "ref": 1, "role": "outer", "geometry": outer["geometry"]},
                                {"type": "way", "ref": 2, "role": "inner", "geometry": inner["geometry"]}]}
        result = self.render([outer, inner, relation])
        self.assertEqual(result["cells"][10][10]["terrain"], "grass")
        self.assertEqual(result["cells"][3][3]["terrain"], "building")
        self.assertEqual(len(result["metadata"]["buildings"]), 1)

    def test_building_priority_and_unknown_land_cover(self):
        forest = self.way(1, [(2, 2), (18, 2), (18, 18), (2, 18), (2, 2)], landuse="forest")
        road = self.way(2, [(1, 10), (19, 10)], highway="residential", width="2")
        building = self.way(3, [(7, 7), (12, 7), (12, 12), (7, 12), (7, 7)], building="house")
        result = self.render([building, road, forest])
        self.assertEqual(result["cells"][10][9]["terrain"], "building")
        self.assertEqual(result["cells"][10][15]["terrain"], "road")
        self.assertEqual(result["cells"][5][5]["obstacleHeight"], 12)
        self.assertFalse(result["cells"][0][0]["landCoverKnown"])

    def test_closed_road_is_linear_and_tunnel_is_skipped(self):
        road = self.way(1, [(2, 2), (18, 2), (18, 18), (2, 18), (2, 2)], highway="residential", width="2")
        self.assertEqual(osm_geometry(road).geom_type, "LineString")
        result = self.render([road])
        self.assertEqual(result["cells"][10][10]["terrain"], "grass")
        road["tags"]["tunnel"] = "yes"
        self.assertEqual(self.render([road])["metadata"]["unknownLandCoverCells"], 400)

    def test_nmt_nodata_rejected_and_grid_orientation_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nmt.tif"
            values = np.arange(400, dtype=np.float32).reshape(20, 20)
            for nodata in [False, True]:
                values[0, 0] = -9999 if nodata else 0
                with rasterio.open(path, "w", driver="GTiff", width=20, height=20, count=1,
                                   dtype="float32", crs="EPSG:2180", transform=self.transform, nodata=-9999) as dest:
                    dest.write(values, 1)
                if nodata:
                    with self.assertRaises(ValueError):
                        read_ground(path, self.transform, 20, 20)
                else:
                    np.testing.assert_equal(read_ground(path, self.transform, 20, 20), values)


class NetworkTests(unittest.TestCase):
    def test_offline_does_not_access_network(self):
        with tempfile.TemporaryDirectory() as directory, patch("uav_routing.maps.osm_importer.urlopen") as network:
            with self.assertRaises(ValueError):
                download("https://example.com", directory, offline=True)
            network.assert_not_called()

    def test_wcs_uses_advertised_coverage_and_xy_bbox(self):
        with tempfile.TemporaryDirectory() as directory:
            capabilities = Path(directory) / "caps.xml"
            capabilities.write_text('<WCS_Capabilities xmlns="http://www.opengis.net/wcs"><ContentMetadata><CoverageOfferingBrief><name>DTM_PL</name></CoverageOfferingBrief></ContentMetadata></WCS_Capabilities>')
            with patch("uav_routing.maps.osm_importer.download", side_effect=[capabilities, Path("nmt.tif")]) as request:
                fetch_nmt((1, 2, 21, 32), 20, 30, directory)
            coverage_url = request.call_args_list[1].args[0]
            self.assertIn("COVERAGE=DTM_PL", coverage_url)
            self.assertIn("BBOX=1%2C2%2C21%2C32", coverage_url)


if __name__ == "__main__":
    unittest.main()
