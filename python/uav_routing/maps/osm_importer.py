"""Import a Polish OSM area and GUGiK ground elevations into the planner grid.

The planner currently assumes one grid step is one metre. Coordinates are cell
centres, x eastwards and y southwards, in EPSG:2180 (not latitude/longitude).
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from shapely import make_valid, transform
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union
from ..paths import ROOT


OVERPASS = "https://overpass-api.de/api/interpreter"
NMT_WCS = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF"
USER_AGENT = "UAVMapImporter/1.0 (OSM + GUGiK research map importer)"
MAX_CELLS = 1_000_000
# Simulation assumptions, not measured heights. Unknown buildings stay explicit.
DEFAULT_HEIGHTS = {
    "house": 8.0, "detached": 8.0, "semidetached_house": 8.0,
    "terrace": 8.0, "apartments": 15.0, "garage": 3.0,
    "garages": 3.0, "shed": 3.0, "industrial": 9.0, "warehouse": 9.0,
}
ROAD_WIDTHS = {"motorway": 14.0, "trunk": 12.0, "primary": 9.0,
               "secondary": 8.0, "tertiary": 7.0, "residential": 6.0,
               "service": 4.0, "footway": 2.0, "path": 2.0,
               "cycleway": 2.5, "track": 3.0, "steps": 2.0}


def number(value):
    """Parse a finite OSM decimal or metric/imperial length; reject ambiguity."""
    if value is None:
        return None
    value = str(value).strip()
    feet = re.fullmatch(r"(\d+(?:\.\d+)?)'(?:\s*(\d+(?:\.\d+)?)\")?", value)
    if feet:
        return float(feet[1]) * 0.3048 + float(feet[2] or 0) * 0.0254
    match = re.fullmatch(r"([+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(m|ft)?", value)
    if not match:
        return None
    result = float(match[1]) * (0.3048 if match[2] == "ft" else 1.0)
    return result if math.isfinite(result) else None


def building_height(tags, unknown_height=12.0):
    explicit = number(tags.get("height"))
    if explicit is not None and 0 < explicit <= 1000:
        return explicit, "osm:height"
    levels = number(tags.get("building:levels"))
    if levels is not None and 0 < levels <= 200:
        roof = number(tags.get("roof:height"))
        if roof is None:
            roof_levels = number(tags.get("roof:levels"))
            roof = roof_levels * 3.0 if roof_levels is not None else (
                0.0 if tags.get("roof:shape") == "flat" else 2.0)
        if 0 <= roof <= 100:
            return levels * 3.0 + roof, "estimated:levels"
    kind = tags.get("building:part", tags.get("building", "yes"))
    if kind in DEFAULT_HEIGHTS:
        return DEFAULT_HEIGHTS[kind], "estimated:type"
    return unknown_height, "estimated:unknown"


def download(url, cache_dir, *, data=None, suffix=".bin", offline=False):
    key = hashlib.sha256(url.encode() + (data or b"")).hexdigest()
    path = Path(cache_dir) / (key + suffix)
    if path.exists():
        return path
    if offline:
        raise ValueError(f"Brak danych w pamięci podręcznej: {path}")
    print(f"Pobieranie: {url.split('?')[0]}", file=sys.stderr)
    request = Request(url, data=data, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=180) as response:
        payload = response.read()
    # Never cache XML service errors or an Overpass timeout as valid data.
    if suffix == ".json":
        parsed = json.loads(payload)
        if "elements" not in parsed or parsed.get("remark"):
            raise ValueError(f"Niepełna odpowiedź Overpass: {parsed.get('remark', 'brak elements')}")
    elif suffix == ".tif" and payload[:4] not in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        raise ValueError(f"WCS nie zwrócił GeoTIFF: {payload[:500]!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return path


def fetch_osm(bounds, cache_dir, endpoint=OVERPASS, offline=False):
    west, south, east, north = Transformer.from_crs(2180, 4326, always_xy=True).transform_bounds(*bounds, densify_pts=21)
    bbox = f"{south:.8f},{west:.8f},{north:.8f},{east:.8f}"
    selectors = ['["building"]', '["building:part"]', '["highway"]',
                 '["landuse"]', '["natural"]', '["waterway"]', '["water"]']
    query = f"[out:json][timeout:120];({''.join(f'nwr{s}({bbox});' for s in selectors)});out geom;"
    path = download(endpoint, cache_dir, data=urlencode({"data": query}).encode(), suffix=".json", offline=offline)
    return json.loads(path.read_text())


def fetch_nmt(bounds, width, height, cache_dir, endpoint=NMT_WCS, offline=False):
    capabilities = download(endpoint + "?" + urlencode({"SERVICE": "WCS", "REQUEST": "GetCapabilities", "VERSION": "1.0.0"}),
                            cache_dir, suffix=".xml", offline=offline)
    root = ET.fromstring(capabilities.read_bytes())
    names = []
    for node in root.iter():
        if node.tag.split("}")[-1] == "CoverageOfferingBrief":
            names.extend(child.text for child in node if child.tag.split("}")[-1] == "name" and child.text)
    if not names:
        raise ValueError("WCS: brak identyfikatora modelu NMT w GetCapabilities")
    params = {"SERVICE": "WCS", "VERSION": "1.0.0", "REQUEST": "GetCoverage",
              "COVERAGE": names[0], "CRS": "EPSG:2180", "RESPONSE_CRS": "EPSG:2180",
              "BBOX": ",".join(map(str, bounds)), "WIDTH": width, "HEIGHT": height, "FORMAT": "GEOTIFF"}
    return download(endpoint + "?" + urlencode(params), cache_dir, suffix=".tif", offline=offline)


def read_ground(path, grid_transform, width, height):
    result = np.full((height, width), np.nan, dtype=np.float32)
    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError("NMT nie ma układu współrzędnych")
        reproject(source=rasterio.band(source, 1), destination=result,
                  src_transform=source.transform, src_crs=source.crs,
                  src_nodata=source.nodata, dst_transform=grid_transform,
                  dst_crs="EPSG:2180", dst_nodata=np.nan, resampling=Resampling.bilinear)
    if not np.isfinite(result).all():
        raise ValueError("NMT nie pokrywa całej mapy lub zawiera NoData; wybierz pełny raster NMT")
    return result


def osm_geometry(element):
    def coordinates(points):
        return [(point["lon"], point["lat"]) for point in points]

    if element["type"] == "way":
        points = element.get("geometry", [])
        if len(points) < 2:
            return None
        coords = coordinates(points)
        tags = element.get("tags", {})
        linear = ("highway" in tags and tags.get("area") != "yes") or tags.get("waterway") in {"river", "canal", "stream", "ditch", "drain"}
        if not linear and len(coords) >= 4 and coords[0] == coords[-1]:
            return make_valid(Polygon(coords))
        return LineString(coords)
    if element["type"] == "relation" and element.get("tags", {}).get("type") == "multipolygon":
        rings = {"outer": [], "inner": []}
        for member in element.get("members", []):
            role = member.get("role") or "outer"
            points = member.get("geometry", [])
            if role in rings and len(points) >= 2:
                rings[role].append(LineString(coordinates(points)))
        outer = unary_union(list(polygonize(unary_union(rings["outer"]))))
        inner = unary_union(list(polygonize(unary_union(rings["inner"]))))
        return make_valid(outer.difference(inner))
    return None


def feature_kind(tags):
    if tags.get("building:part", "no") != "no" or tags.get("building", "no") != "no":
        return "building"
    if "highway" in tags and tags.get("area") != "yes":
        return "road"
    if tags.get("natural") == "water" or "water" in tags or tags.get("waterway") == "riverbank" or tags.get("landuse") in {"reservoir", "basin"}:
        return "water"
    if tags.get("waterway") in {"river", "canal", "stream", "ditch", "drain"}:
        return "water"
    if tags.get("natural") == "wood" or tags.get("landuse") == "forest":
        return "forest"
    if tags.get("landuse") in {"grass", "meadow", "farmland", "farmyard", "recreation_ground"} or tags.get("natural") in {"grassland", "heath"}:
        return "grass"
    return None


def build_map(osm, ground, grid_transform, metadata, unknown_height=12.0, forest_height=12.0):
    height, width = ground.shape
    area = box(*rasterio.transform.array_bounds(height, width, grid_transform))
    project = Transformer.from_crs(4326, 2180, always_xy=True).transform
    def project_coordinates(coordinates):
        return np.column_stack(project(coordinates[:, 0], coordinates[:, 1]))
    features = []
    # A tagged multipolygon member is represented by its relation, including holes.
    member_ids = {member["ref"] for element in osm["elements"]
                  if element["type"] == "relation" and element.get("tags", {}).get("type") == "multipolygon" and feature_kind(element.get("tags", {}))
                  for member in element.get("members", []) if member["type"] == "way"}
    for element in osm["elements"]:
        if element["type"] == "way" and element["id"] in member_ids:
            continue
        tags = element.get("tags", {})
        kind = feature_kind(tags)
        if kind is None or tags.get("tunnel") in {"yes", "building_passage"}:
            continue
        geometry = osm_geometry(element)
        if geometry is None or geometry.is_empty:
            continue
        geometry = transform(geometry, project_coordinates)
        if kind in {"road", "water"} and geometry.geom_type in {"LineString", "MultiLineString"}:
            default = ROAD_WIDTHS.get(tags.get("highway"), 5.0) if kind == "road" else 3.0
            road_width = number(tags.get("width"))
            road_width = road_width if road_width is not None and 0 < road_width <= 100 else default
            geometry = geometry.buffer(road_width / 2)
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            continue
        geometry = geometry.intersection(area)
        if not geometry.is_empty:
            features.append((kind, geometry, tags, f"{element['type']}/{element['id']}"))

    terrain = np.full(ground.shape, "grass", dtype=object)
    known = np.zeros(ground.shape, dtype=bool)
    surface = ground.copy()
    building_ids = np.full(ground.shape, "", dtype=object)
    buildings = []
    priorities = {"grass": 0, "forest": 1, "water": 2, "road": 3, "building": 4}
    # Parts replace outline heights in their footprint; overlapping parts use maximum.
    features.sort(key=lambda feature: (priorities[feature[0]], "building:part" in feature[2], feature[3]))
    outlines = [(geom, building_height(tags, unknown_height)[0]) for kind, geom, tags, _ in features
                if kind == "building" and "building:part" not in tags]
    part_surface = np.full(ground.shape, -np.inf, dtype=np.float32)
    for kind, geometry, tags, osm_id in features:
        mask = geometry_mask([geometry], ground.shape, grid_transform, invert=True, all_touched=True)
        if not mask.any():
            continue
        if kind == "building":
            building_h, source = building_height(tags, unknown_height)
            base = float(ground[mask].min())
            if "building:part" in tags:
                parents = [geom for geom, _ in outlines if geom.covers(geometry.representative_point())]
                if parents:
                    parent_mask = geometry_mask([min(parents, key=lambda g: g.area)], ground.shape, grid_transform, invert=True, all_touched=True)
                    base = float(ground[parent_mask].min())
                roof = np.maximum(ground, base + building_h)
                update = mask & (roof > part_surface)
                surface[update] = roof[update]
                part_surface[update] = roof[update]
            else:
                roof = np.maximum(ground, base + building_h)
                update = mask & ((terrain != "building") | (roof > surface))
                surface[update] = roof[update]
            building_ids[update] = osm_id
            buildings.append({"id": osm_id, "type": tags.get("building:part", tags.get("building", "yes")),
                              "height": building_h, "heightSource": source,
                              "baseElevation": base, "estimated": source != "osm:height"})
        else:
            surface[mask] = ground[mask] + (forest_height if kind == "forest" else 0)
        terrain[mask] = kind
        known[mask] = True

    cells = []
    concealment = {"grass": 0.1, "forest": 0.8, "water": 0.0, "road": 0.0, "building": 0.0}
    for y in range(height):
        row = []
        for x in range(width):
            kind = terrain[y, x]
            cell = {"terrain": kind, "elevation": round(float(surface[y, x]), 3),
                    "groundElevation": round(float(ground[y, x]), 3),
                    "obstacleHeight": round(float(surface[y, x] - ground[y, x]), 3),
                    "landCoverKnown": bool(known[y, x]), "obstacle": False,
                    "concealment": concealment[kind], "threatLevel": 0.0}
            if building_ids[y, x]:
                cell["buildingId"] = building_ids[y, x]
            row.append(cell)
        cells.append(row)
    metadata = dict(metadata)
    metadata.update({"buildings": buildings, "heightSources": dict(Counter(b["heightSource"] for b in buildings)),
                     "unknownLandCoverCells": int((~known).sum()),
                     "assumptions": {"unknownBuildingHeight": unknown_height, "forestHeight": forest_height,
                                     "floorHeight": 3.0, "defaultRoofHeight": 2.0,
                                     "buildingTypeHeights": DEFAULT_HEIGHTS,
                                     "unknownLandCover": "grass", "elevatedStructures": "solid columns to ground"}})
    return {"width": width, "height": height, "metadata": metadata, "cells": cells, "radars": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--center", nargs=2, type=float, required=True, metavar=("LAT", "LON"))
    parser.add_argument("--size", nargs=2, type=int, default=[200, 200], metavar=("WIDTH_M", "HEIGHT_M"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data/cache/map-import")
    parser.add_argument("--osm-file", type=Path, help="Lokalny JSON Overpass (out geom)")
    parser.add_argument("--dem", type=Path, help="Lokalny raster NMT z georeferencją zamiast WCS")
    parser.add_argument("--offline", action="store_true", help="Wyłącznie pliki lokalne/pamięć podręczna")
    parser.add_argument("--overpass-url", default=OVERPASS)
    parser.add_argument("--wcs-url", default=NMT_WCS)
    parser.add_argument("--unknown-building-height", type=float, default=12.0)
    parser.add_argument("--forest-height", type=float, default=12.0)
    args = parser.parse_args()
    lat, lon = args.center
    width, height = args.size
    if not (49 <= lat <= 55 and 14 <= lon <= 24.2):
        parser.error("Wybierz środek w Polsce: --center LAT LON")
    if width <= 0 or height <= 0 or width * height > MAX_CELLS:
        parser.error(f"Rozmiar musi być dodatni i nie przekraczać {MAX_CELLS} komórek (1 m²)")
    if not (0 < args.unknown_building_height <= 1000 and 0 <= args.forest_height <= 100):
        parser.error("Niepoprawna wysokość zastępcza budynku lub lasu")
    east, north = Transformer.from_crs(4326, 2180, always_xy=True).transform(lon, lat)
    west, south = math.floor(east - width / 2), math.floor(north - height / 2)
    bounds = (west, south, west + width, south + height)
    grid_transform = from_origin(west, south + height, 1, 1)
    try:
        osm = json.loads(args.osm_file.read_text()) if args.osm_file else fetch_osm(bounds, args.cache_dir, args.overpass_url, args.offline)
        if osm.get("remark") or not isinstance(osm.get("elements"), list):
            raise ValueError("Niepełny lub niepoprawny JSON Overpass")
        dem = args.dem or fetch_nmt(bounds, width, height, args.cache_dir, args.wcs_url, args.offline)
        ground = read_ground(dem, grid_transform, width, height)
        metadata = {"schemaVersion": 1, "source": "osm+nmt", "crs": "EPSG:2180", "cellSizeMeters": 1.0,
                    "bounds": list(bounds), "origin": "north-west", "coordinates": "cell centres, x east, y south",
                    "centerLatLon": [lat, lon], "createdAt": datetime.now(timezone.utc).isoformat(),
                    "attribution": "© OpenStreetMap contributors; NMT: GUGiK / Geoportal.gov.pl",
                    "osmLicense": "https://www.openstreetmap.org/copyright",
                    "osmSource": str(args.osm_file or args.overpass_url),
                    "demSource": str(args.dem or args.wcs_url),
                    "demVerticalDatum": "source raster datum; no vertical transformation",
                    "osmTimestamp": osm.get("osm3s", {}).get("timestamp_osm_base")}
        result = build_map(osm, ground, grid_transform, metadata, args.unknown_building_height, args.forest_height)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(args.output)
        print(f"Zapisano {width} × {height} m: {args.output}")
        print("Źródła wysokości budynków:", result["metadata"]["heightSources"])
        print("Komórki o nieznanym pokryciu:", result["metadata"]["unknownLandCoverCells"])
    except (OSError, ValueError, ET.ParseError, rasterio.errors.RasterioError) as error:
        parser.exit(1, f"Błąd importu: {error}\n")


if __name__ == "__main__":
    main()
