#!/usr/bin/env python3
"""
AFTERSHOCK — Seismic Data Fetcher
───────────────────────────────────────────────────────────────────────────────
Pulls the last 30 days of earthquake data from the USGS Earthquake Hazards
Program API and writes static JSON for the dashboard.

Data source: https://earthquake.usgs.gov/fdsnws/event/1/
"""

import requests
import json
import re
import os
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ─── Constants ────────────────────────────────────────────────────────────────

USGS_API      = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DATA_DIR      = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE   = os.path.join(DATA_DIR, "earthquakes.json")
PERIOD_DAYS   = 30
MIN_MAG       = 1.5

# Energy yield of the Hiroshima "Little Boy" bomb ≈ 6.3 × 10¹³ J
HIROSHIMA_J   = 6.3e13

STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas",
    "CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware",
    "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho",
    "IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas",
    "KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
    "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
    "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina",
    "SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah",
    "VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia",
    "WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia",
    "PR":"Puerto Rico","VI":"Virgin Islands","GU":"Guam",
    "AS":"American Samoa","MP":"Northern Mariana Islands"
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def seismic_energy_joules(mag: float) -> float:
    """Gutenberg-Richter energy formula: E = 10^(1.5·M + 4.8) joules."""
    return 10 ** (1.5 * mag + 4.8)

def extract_state(place: str) -> str | None:
    """Parse US state abbreviation from a USGS place description string.
    
    Handles patterns like:
      "5km NE of Berkeley, CA"
      "15 km ESE of Ridgecrest, California"
      "Hawaii region, Hawaii"
    """
    if not place:
        return None

    # Pattern 1: ends with ", XX" (two-letter abbreviation)
    m = re.search(r",\s*([A-Z]{2})\s*$", place)
    if m and m.group(1) in STATE_NAMES:
        return m.group(1)

    # Pattern 2: full state name present in string
    place_lower = place.lower()
    for abbr, name in STATE_NAMES.items():
        if f", {name.lower()}" in place_lower or place_lower.endswith(name.lower()):
            return abbr

    return None

def mag_bucket(mag: float) -> str:
    if mag < 2.0: return "M1"
    if mag < 3.0: return "M2"
    if mag < 4.0: return "M3"
    if mag < 5.0: return "M4"
    if mag < 6.0: return "M5"
    return "M6+"

def depth_class(depth: float) -> str:
    """USGS depth classification thresholds."""
    if depth < 70:  return "shallow"
    if depth < 300: return "intermediate"
    return "deep"

# ─── Fetch ────────────────────────────────────────────────────────────────────

def fetch_earthquakes() -> list:
    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=PERIOD_DAYS)

    params = {
        "format":       "geojson",
        "starttime":    start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime":      end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": MIN_MAG,
        "orderby":      "time",
        "limit":        20000,
    }

    print(f"  Querying USGS: M≥{MIN_MAG}, past {PERIOD_DAYS} days...")
    resp = requests.get(USGS_API, params=params, timeout=60)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    print(f"  Retrieved {len(features):,} features from USGS ComCat")
    return features

# ─── Process ──────────────────────────────────────────────────────────────────

def process(features: list) -> dict:
    earthquakes   = []
    state_buckets = defaultdict(lambda: {
        "count": 0, "mags": [], "depths": [],
        "max_mag": 0.0, "max_place": "", "max_time": 0,
        "significant": []
    })
    total_energy = 0.0

    for f in features:
        props  = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [None, None, None])

        mag = props.get("mag")
        if mag is None:
            continue

        place   = props.get("place", "") or ""
        time_ms = props.get("time",  0)  or 0
        lon, lat, depth = coords[0], coords[1], float(coords[2] or 0.0)
        state   = extract_state(place)
        energy  = seismic_energy_joules(float(mag))
        total_energy += energy

        eq = {
            "id":    f.get("id", ""),
            "mag":   round(float(mag), 1),
            "place": place,
            "time":  time_ms,
            "lat":   round(float(lat), 4) if lat is not None else None,
            "lon":   round(float(lon), 4) if lon is not None else None,
            "depth": round(depth, 1),
            "state": state,
            "url":   props.get("url", "")
        }
        earthquakes.append(eq)

        if state:
            sb = state_buckets[state]
            sb["count"] += 1
            sb["mags"].append(float(mag))
            sb["depths"].append(depth)
            if float(mag) > sb["max_mag"]:
                sb["max_mag"]   = float(mag)
                sb["max_place"] = place
                sb["max_time"]  = time_ms
            if float(mag) >= 3.0:
                sb["significant"].append({
                    "mag":   round(float(mag), 1),
                    "place": place,
                    "time":  time_ms,
                    "depth": round(depth, 1)
                })

    # Build per-state stats
    state_stats = {}
    for abbr, sb in state_buckets.items():
        mags, depths = sb["mags"], sb["depths"]

        dist  = {"M1":0,"M2":0,"M3":0,"M4":0,"M5":0,"M6+":0}
        ddist = {"shallow":0,"intermediate":0,"deep":0}
        for m in mags:  dist[mag_bucket(m)] += 1
        for d in depths: ddist[depth_class(d)] += 1

        sig = sorted(sb["significant"], key=lambda x: x["mag"], reverse=True)[:10]

        state_stats[abbr] = {
            "name":               STATE_NAMES.get(abbr, abbr),
            "count":              sb["count"],
            "max_mag":            round(sb["max_mag"], 1),
            "max_place":          sb["max_place"],
            "max_time":           sb["max_time"],
            "avg_mag":            round(sum(mags)   / len(mags),   2) if mags   else 0,
            "avg_depth":          round(sum(depths) / len(depths), 1) if depths else 0,
            "mag_distribution":   dist,
            "depth_distribution": ddist,
            "significant":        sig
        }

    # National summary
    all_mags = [e["mag"] for e in earthquakes]
    largest  = max(earthquakes, key=lambda x: x["mag"]) if earthquakes else {}

    summary = {
        "total_count":        len(earthquakes),
        "period_days":        PERIOD_DAYS,
        "min_magnitude":      MIN_MAG,
        "max_mag":            round(max(all_mags), 1) if all_mags else 0,
        "avg_mag":            round(sum(all_mags) / len(all_mags), 2) if all_mags else 0,
        "largest_place":      largest.get("place", ""),
        "largest_time":       largest.get("time",  0),
        "states_active":      len(state_stats),
        "total_energy_joules": total_energy,
        "hiroshima_equiv":    round(total_energy / HIROSHIMA_J, 1)
    }

    return {
        "generated":   datetime.now(timezone.utc).isoformat(),
        "summary":     summary,
        "earthquakes": earthquakes,
        "state_stats": state_stats
    }

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║          AFTERSHOCK  ·  Data Fetch        ║")
    print("╚══════════════════════════════════════════╝\n")

    os.makedirs(DATA_DIR, exist_ok=True)

    features = fetch_earthquakes()
    output   = process(features)

    with open(OUTPUT_FILE, "w") as fh:
        json.dump(output, fh, separators=(",", ":"))

    s = output["summary"]
    print(f"\n  ✓  {s['total_count']:,} earthquakes written to {OUTPUT_FILE}")
    print(f"  ✓  {s['states_active']} states / territories with seismic activity")
    print(f"  ✓  Largest: M{s['max_mag']} — {s['largest_place']}")
    print(f"  ✓  Total seismic energy: {s['hiroshima_equiv']:,.1f}× Hiroshima\n")

if __name__ == "__main__":
    main()
