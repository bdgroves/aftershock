"""
geo.py — boundaries and "where is this earthquake?" for AFTERSHOCK.

Boundaries are Natural Earth (public domain), simplified once and committed
under data/geo/ so neither the pipeline nor the page depends on a third-party
URL at run time:

  countries_attr.json  50m countries, rounded to ~100 m — for attribution
  countries.json       110m countries — what the page draws
  us_states.json       50m US states  — attribution and the page

Attribution: point-in-polygon on land; offshore events go to the nearest
country (or US state) within OFFSHORE_KM, flagged offshore=True; anything
further out is "ocean" and keeps USGS's own region name (e.g. "Mid-Atlantic
Ridge"). Pure Python, no shapely/GDAL, so the pixi environment stays tiny.
"""

import json
import math
import os

import requests

GEO_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "geo")
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
OFFSHORE_KM = 250          # nearest-country distance for offshore events
OFFSHORE_STATE_KM = 200    # nearest-state distance (e.g. off Cape Mendocino → CA)

US_TERRITORIES = {"PR": "Puerto Rico", "VI": "U.S. Virgin Islands", "GU": "Guam",
                  "MP": "Northern Mariana Islands", "AS": "American Samoa", "UM": "U.S. Minor Outlying Islands"}


# ── building the committed files (runs once, or when a file is missing) ──────
def _round_geom(geom, nd):
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], nd), round(c[1], nd)]
        return [r(x) for x in c]
    out = {"type": geom["type"], "coordinates": r(geom["coordinates"])}
    # drop consecutive duplicate vertices created by rounding
    def dedupe(ring):
        res = [ring[0]]
        for p in ring[1:]:
            if p != res[-1]:
                res.append(p)
        return res if len(res) >= 4 else ring
    if out["type"] == "Polygon":
        out["coordinates"] = [dedupe(x) for x in out["coordinates"]]
    elif out["type"] == "MultiPolygon":
        out["coordinates"] = [[dedupe(x) for x in poly] for poly in out["coordinates"]]
    return out


def _cc(p):
    for k in ("ISO_A2_EH", "ISO_A2", "WB_A2"):
        v = p.get(k)
        if v and v != "-99":
            return v
    return p.get("ADM0_A3", "??")[:2]


def build_geo_files():
    os.makedirs(GEO_DIR, exist_ok=True)
    for res, name, nd in (("50m", "countries_attr.json", 3), ("110m", "countries.json", 2)):
        path = os.path.join(GEO_DIR, name)
        if os.path.exists(path):
            continue
        gj = requests.get(NE + f"ne_{res}_admin_0_countries.geojson", timeout=180).json()
        feats = []
        for f in gj["features"]:
            p = f["properties"]
            feats.append({"type": "Feature", "geometry": _round_geom(f["geometry"], nd),
                          "properties": {"cc": _cc(p), "name": p.get("NAME") or p.get("ADMIN"),
                                         "continent": p.get("CONTINENT"), "region": p.get("REGION_UN"),
                                         "subregion": p.get("SUBREGION")}})
        json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"), separators=(",", ":"))
        print(f"  built {name} ({len(feats)} countries)")
    path = os.path.join(GEO_DIR, "us_states.json")
    if not os.path.exists(path):
        gj = requests.get(NE + "ne_50m_admin_1_states_provinces.geojson", timeout=180).json()
        feats = []
        for f in gj["features"]:
            p = f["properties"]
            if p.get("adm0_a3") != "USA":
                continue
            code = (p.get("postal") or (p.get("iso_3166_2") or "US-??")[3:])
            feats.append({"type": "Feature", "geometry": _round_geom(f["geometry"], 3),
                          "properties": {"st": code, "name": p.get("name")}})
        json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"), separators=(",", ":"))
        print(f"  built us_states.json ({len(feats)} states)")


# ── geometry ─────────────────────────────────────────────────────────────────
def _polys(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _in_poly(x, y, poly):
    return _in_ring(x, y, poly[0]) and not any(_in_ring(x, y, h) for h in poly[1:])


def _bbox(polys):
    xs = [p[0] for poly in polys for p in poly[0]]
    ys = [p[1] for poly in polys for p in poly[0]]
    return min(xs), min(ys), max(xs), max(ys)


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(min(1, math.sqrt(a)))


class Locator:
    """Answers: which country (and US state) is this point in, or nearest to?"""

    def __init__(self):
        build_geo_files()
        self.countries = self._load("countries_attr.json", "cc")
        self.states = self._load("us_states.json", "st")
        self.meta = {}
        for f in json.load(open(os.path.join(GEO_DIR, "countries_attr.json")))["features"]:
            p = f["properties"]
            self.meta.setdefault(p["cc"], {"name": p["name"], "continent": p["continent"],
                                           "region": p["region"], "subregion": p["subregion"]})
        self.state_names = {s["key"]: s["name"] for s in self.states["items"]}
        self._memo = {}

    @staticmethod
    def _load(name, key):
        """Polygons with their own bounding boxes, plus a 1° grid of coastline
        vertices so the offshore nearest-neighbour search only looks nearby."""
        out, grid = [], {}
        for f in json.load(open(os.path.join(GEO_DIR, name)))["features"]:
            k = f["properties"][key]
            polys = [(poly, _bbox([poly])) for poly in _polys(f["geometry"])]
            out.append({"key": k, "name": f["properties"]["name"], "polys": polys,
                        "bbox": _bbox([p for p, _ in polys])})
            for poly, _ in polys:
                for vx, vy in poly[0]:
                    grid.setdefault((math.floor(vy), math.floor(vx)), []).append((vy, vx, k))
        return {"items": out, "grid": grid}

    def _find(self, layer, lon, lat, max_km):
        for it in layer["items"]:
            x0, y0, x1, y1 = it["bbox"]
            if not (x0 <= lon <= x1 and y0 <= lat <= y1):
                continue
            for poly, (a0, b0, a1, b1) in it["polys"]:
                if a0 <= lon <= a1 and b0 <= lat <= b1 and _in_poly(lon, lat, poly):
                    return it["key"], False
        best, best_d = None, max_km
        dlat = int(max_km / 111) + 1
        dlon = int(max_km / (111 * max(0.05, math.cos(math.radians(lat))))) + 1
        cy, cx = math.floor(lat), math.floor(lon)
        for gy in range(cy - dlat, cy + dlat + 1):
            for gx in range(cx - dlon, cx + dlon + 1):
                gxw = ((gx + 180) % 360) - 180          # wrap across the antimeridian
                for vy, vx, k in layer["grid"].get((gy, gxw), ()):
                    d = haversine_km(lat, lon, vy, vx)
                    if d < best_d:
                        best, best_d = k, d
        return (best, True) if best else (None, None)

    def locate(self, lon, lat):
        """→ (cc, state, offshore). cc None = open ocean. Memoised to ~1 km."""
        key = (round(lon, 2), round(lat, 2))
        hit = self._memo.get(key)
        if hit is None:
            hit = self._memo[key] = self._locate(lon, lat)
        return hit

    def _locate(self, lon, lat):
        cc, off = self._find(self.countries, lon, lat, OFFSHORE_KM)
        state = None
        if cc == "US" or cc is None or (cc in ("CA", "MX") and off):
            st, st_off = self._find(self.states, lon, lat, OFFSHORE_STATE_KM if cc in (None, "US") else 60)
            if st:
                state = st
                if cc != "US":
                    cc, off = "US", st_off
        return cc, state, bool(off)
