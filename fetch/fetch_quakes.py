#!/usr/bin/env python3
"""
AFTERSHOCK — Seismic Data Fetcher
───────────────────────────────────────────────────────────────────────────────
Pulls the last 30 days of earthquakes (M1.5+, worldwide) from the USGS ComCat
API and writes static JSON for the dashboard:

  data/earthquakes.json  every event, compact columns, tagged with country,
                         US state and aftershock sequence; plus the sequences
  data/baselines.json    10 complete years of counts per country (M4.5+) and
                         per US state (M2.5+), rebuilt weekly — "is this normal?"

A note on fairness. ComCat is complete to about M1.5 where the US runs dense
networks (California, Alaska, Hawaii, Utah, Nevada, Washington…), but only to
about M4.5 for most of the world. So counts are compared at M4.5+ between
countries and at M2.5+ between US states. Comparing raw M1.5+ counts mostly
measures how many seismometers a place has.

Data source: https://earthquake.usgs.gov/fdsnws/event/1/
"""

import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(__file__))
from geo import US_TERRITORIES, Locator, haversine_km  # noqa: E402

USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "earthquakes.json")
BASELINE_FILE = os.path.join(DATA_DIR, "baselines.json")
PERIOD_DAYS = 30
MIN_MAG = 1.5
WORLD_MC = 4.5      # magnitude above which the global catalog is ~complete
US_MC = 2.5         # same, for the US networks (conservative)
BASELINE_YEARS = 10
HIROSHIMA_J = 6.3e13  # "Little Boy", ≈ 15 kt TNT
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "AFTERSHOCK (github.com/bdgroves/aftershock)"

# US regions for the baseline queries (lat0, lat1, lon0, lon1)
US_BOXES = [(24, 50, -125.5, -66), (50, 72, -180, -129), (50, 56, 170, 180),
            (18, 23, -161, -154), (17, 19.5, -68, -64), (12, 21, 143, 147)]


def energy_j(mag):
    """Gutenberg–Richter energy: log10 E = 1.5 M + 4.8 (joules)."""
    return 10 ** (1.5 * mag + 4.8)


def query(params, retries=3):
    for attempt in range(retries):
        try:
            r = SESSION.get(USGS_API, params={"format": "geojson", "limit": 20000, **params}, timeout=180)
            r.raise_for_status()
            return r.json().get("features", [])
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  retry ({e})")
            time.sleep(10 * (attempt + 1))


# ── Aftershock sequences ─────────────────────────────────────────────────────
def gk_window(mag):
    """Gardner & Knopoff (1974) space–time window: (km, days)."""
    km = 10 ** (0.1238 * mag + 0.983)
    days = 10 ** (0.032 * mag + 2.7389) if mag >= 6.5 else 10 ** (0.5409 * mag - 0.547)
    return km, days


def find_sequences(events):
    """Window declustering: biggest events first claim the smaller events inside
    their Gardner–Knopoff window. Returns sequences with ≥ 3 aftershocks.

    Only events at or above the local completeness magnitude are counted, so
    sequences are comparable (US M2.5+, elsewhere M4.5+ — see module notes)."""
    def mc(e):
        return US_MC if e["cc"] in ("US",) or e["cc"] in US_TERRITORIES else WORLD_MC
    usable = [e for e in events if e["mag"] >= mc(e) - 1e-9]
    order = sorted(usable, key=lambda e: -e["mag"])
    claimed = {}
    seqs = []
    for main in order:
        if main["id"] in claimed:
            continue
        km, days = gk_window(main["mag"])
        members = []
        for e in usable:
            if e is main or e["id"] in claimed or e["mag"] > main["mag"]:
                continue
            dt = (e["time"] - main["time"]) / 86400000
            if -days <= dt <= days and haversine_km(main["lat"], main["lon"], e["lat"], e["lon"]) <= km:
                members.append((dt, e))
        after = [e for dt, e in members if dt >= 0]
        fore = [e for dt, e in members if dt < 0]
        for _, e in members:
            claimed[e["id"]] = main["id"]
        claimed[main["id"]] = main["id"]
        if len(after) < 3:
            continue
        span = max(1, math.ceil((max(e["time"] for e in after) - main["time"]) / 86400000))
        daily = [0] * (span + 1)
        for e in after:
            daily[int((e["time"] - main["time"]) // 86400000)] += 1
        big = max(after, key=lambda e: e["mag"])
        seq = {
            "id": main["id"], "mag": main["mag"], "place": main["place"], "time": main["time"],
            "lat": main["lat"], "lon": main["lon"], "depth": main["depth"],
            "cc": main["cc"], "state": main["state"],
            "n_after": len(after), "n_fore": len(fore), "mc": mc(main),
            "largest_after": big["mag"], "bath_dm": round(main["mag"] - big["mag"], 1),
            # Båth's law: the largest aftershock is typically ~1.2 smaller. Much
            # less than that, and it behaves more like a swarm than a mainshock–aftershock sequence.
            "kind": "swarm" if main["mag"] - big["mag"] < 0.5 else "mainshock",
            "radius_km": round(km), "window_days": round(days),
            "daily": daily, "members": [e["id"] for e in after],
        }
        seq["omori_p"] = omori_p(daily)
        seqs.append(seq)
    seqs.sort(key=lambda s: (-s["n_after"], -s["mag"]))
    return seqs, claimed


def omori_p(daily, c=0.05):
    """Decay exponent p of the modified Omori law n(t) = K / (t + c)^p, from a
    least-squares line through log daily counts. None if too few aftershocks."""
    pts = [(math.log10(t + 0.5 + c), math.log10(n)) for t, n in enumerate(daily) if n > 0]
    if sum(daily) < 20 or len(pts) < 4:
        return None
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if not sxx:
        return None
    slope = sum((x - mx) * (y - my) for x, y in pts) / sxx
    return round(-slope, 2)


# ── Baselines: 10 complete years ─────────────────────────────────────────────
def build_baselines(loc):
    this_year = date.today().year
    years = list(range(this_year - BASELINE_YEARS, this_year))
    world = defaultdict(lambda: defaultdict(int))     # key → year → count (M4.5+)
    us = defaultdict(lambda: defaultdict(int))        # state/territory → year → count (M2.5+)
    for y in years:
        feats = query({"starttime": f"{y}-01-01", "endtime": f"{y + 1}-01-01", "minmagnitude": WORLD_MC})
        for f in feats:
            lon, lat = f["geometry"]["coordinates"][:2]
            cc, st, _ = loc.locate(lon, lat)
            meta = loc.meta.get(cc, {})
            for k in ("world", cc or "OCEAN", "R:" + (meta.get("region") or "Oceans"),
                      "S:" + (meta.get("subregion") or "Oceans")):
                world[k][y] += 1
        print(f"  baseline {y}: {len(feats):,} M{WORLD_MC}+ worldwide")
        seen = set()
        n = 0
        for b in US_BOXES:
            for f in query({"starttime": f"{y}-01-01", "endtime": f"{y + 1}-01-01", "minmagnitude": US_MC,
                            "minlatitude": b[0], "maxlatitude": b[1], "minlongitude": b[2], "maxlongitude": b[3]}):
                if f["id"] in seen:
                    continue
                seen.add(f["id"])
                lon, lat = f["geometry"]["coordinates"][:2]
                cc, st, _ = loc.locate(lon, lat)
                if cc == "US" or cc in US_TERRITORIES:
                    us["USA"][y] += 1
                    us[st or cc][y] += 1
                    n += 1
        print(f"  baseline {y}: {n:,} M{US_MC}+ in the US")
    pack = lambda d: {k: [v.get(y, 0) for y in years] for k, v in sorted(d.items())}
    return {"built": date.today().isoformat(), "years": years,
            "world_mc": WORLD_MC, "us_mc": US_MC, "world": pack(world), "us": pack(us)}


def load_or_build_baselines(loc):
    old = json.load(open(BASELINE_FILE)) if os.path.exists(BASELINE_FILE) else None
    if old and (date.today() - date.fromisoformat(old["built"])).days < 7 \
            and old["years"][-1] == date.today().year - 1:
        return old, False
    try:
        return build_baselines(loc), True
    except Exception as e:
        print(f"  ⚠ baseline rebuild failed ({e}) — keeping the old one")
        return old, False


# ── Main processing ──────────────────────────────────────────────────────────
FIELDS = ["id", "time", "mag", "magType", "lat", "lon", "depth", "place", "cc", "state", "offshore",
          "alert", "tsunami", "felt", "sig", "mmi", "status", "net", "seq", "role"]


def state_from_place(place, loc):
    """Last resort for US events with no state polygon nearby (the western
    Aleutians sit across the antimeridian from Natural Earth's Alaska)."""
    if "aleutian" in place.lower():
        return "AK"
    tail = place.rsplit(",", 1)[-1].strip().lower()
    for st, name in loc.state_names.items():
        if tail in (st.lower(), (name or "").lower()):
            return st
    return None


def process(features, loc):
    events = []
    for f in features:
        p = f.get("properties", {})
        c = f.get("geometry", {}).get("coordinates") or [None, None, None]
        if p.get("mag") is None or c[0] is None or p.get("type") not in (None, "earthquake"):
            continue
        cc, st, off = loc.locate(c[0], c[1])
        if cc == "US" and not st:
            st = state_from_place(p.get("place") or "", loc)
        events.append({
            "id": f.get("id", ""), "time": p.get("time") or 0, "mag": round(float(p["mag"]), 1),
            "magType": p.get("magType"), "lat": round(c[1], 4), "lon": round(c[0], 4),
            "depth": round(float(c[2] or 0), 1), "place": p.get("place") or "",
            "cc": cc, "state": st, "offshore": off, "alert": p.get("alert"),
            "tsunami": p.get("tsunami") or 0, "felt": p.get("felt"), "sig": p.get("sig"),
            "mmi": round(p["mmi"], 1) if p.get("mmi") is not None else None,
            "status": p.get("status"), "net": p.get("net"), "seq": None, "role": None,
        })
    events.sort(key=lambda e: -e["time"])

    seqs, claimed = find_sequences(events)
    seq_ids = {s["id"] for s in seqs}
    for e in events:
        m = claimed.get(e["id"])
        if m in seq_ids:
            e["seq"] = m
            e["role"] = "main" if m == e["id"] else ("after" if e["id"] in next(s for s in seqs if s["id"] == m)["members"] else "fore")
    for s in seqs:
        s.pop("members")

    total_e = sum(energy_j(e["mag"]) for e in events)
    biggest = max(events, key=lambda e: e["mag"]) if events else None
    names = {cc: dict(loc.meta[cc]) for cc in {e["cc"] for e in events} if cc in loc.meta}
    states = {st: loc.state_names.get(st, st) for st in {e["state"] for e in events if e["state"]}}
    by_cc = Counter(e["cc"] or "OCEAN" for e in events)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period_days": PERIOD_DAYS, "min_mag": MIN_MAG,
        "world_mc": WORLD_MC, "us_mc": US_MC,
        "summary": {
            "total_count": len(events),
            "max_mag": biggest["mag"] if biggest else None,
            "largest_place": biggest["place"] if biggest else "",
            "largest_time": biggest["time"] if biggest else None,
            "total_energy_joules": total_e,
            "hiroshima_equiv": round(total_e / HIROSHIMA_J, 1),
            "largest_share_of_energy": round(energy_j(biggest["mag"]) / total_e, 3) if biggest else None,
            "countries_active": len([k for k in by_cc if k != "OCEAN"]),
            "us_count": sum(1 for e in events if e["cc"] == "US" or e["cc"] in US_TERRITORIES),
        },
        "countries": names,
        "states": states,
        "us_territories": US_TERRITORIES,
        "fields": FIELDS,
        "events": [[e[k] for k in FIELDS] for e in events],
        "sequences": seqs,
    }


def main():
    print("\n  AFTERSHOCK · data fetch\n")
    os.makedirs(DATA_DIR, exist_ok=True)
    loc = Locator()
    end = datetime.now(timezone.utc)
    feats = query({"starttime": (end - timedelta(days=PERIOD_DAYS)).strftime("%Y-%m-%dT%H:%M:%S"),
                   "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"), "minmagnitude": MIN_MAG, "orderby": "time"})
    print(f"  {len(feats):,} events from ComCat")
    if len(feats) < 500:
        # a normal 30 days is ~5,000+; a near-empty answer is an API problem, not a quiet planet
        print(f"::error::Only {len(feats)} events returned — keeping the published file")
        sys.exit(1)
    out = process(feats, loc)
    with open(OUTPUT_FILE, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))

    base, rebuilt = load_or_build_baselines(loc)
    if rebuilt and base:
        with open(BASELINE_FILE, "w") as fh:
            json.dump(base, fh, separators=(",", ":"))

    s = out["summary"]
    print(f"  ✓ {s['total_count']:,} events · {s['us_count']:,} in the US · {s['countries_active']} countries")
    print(f"  ✓ largest M{s['max_mag']} — {s['largest_place']}")
    print(f"  ✓ {len(out['sequences'])} aftershock sequences · baselines {'rebuilt' if rebuilt else 'kept'}")
    big_new = [e for e in out["events"] if e[2] >= 4.5]
    with open(os.path.join(DATA_DIR, ".commit_hint"), "w") as fh:
        # newest M4.5+ id, so the workflow can commit at once when a new one appears
        fh.write((big_new[0][0] if big_new else "") + "\n")


if __name__ == "__main__":
    main()
