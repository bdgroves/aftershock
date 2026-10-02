"""Probe in Actions: boundary sources, USGS counts for baselines, place-string patterns."""
import json, traceback, collections
import requests
out = {}
def step(k, f):
    try: out[k] = f()
    except Exception: out[k] = {"error": traceback.format_exc()[-1200:]}
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
def ne(name):
    r = requests.get(NE + name, timeout=120); r.raise_for_status()
    gj = r.json(); f0 = gj["features"][0]["properties"]
    return {"bytes": len(r.content), "n": len(gj["features"]), "keys": sorted(f0)[:80],
            "sample": {k: f0.get(k) for k in ("NAME","ISO_A2","ISO_A2_EH","ADM0_A3","REGION_UN","SUBREGION","CONTINENT","name","iso_a2","adm0_a3","postal","iso_3166_2") if k in f0}}
for n in ["ne_50m_admin_0_countries.geojson","ne_110m_admin_0_countries.geojson","ne_50m_admin_1_states_provinces.geojson","ne_10m_admin_0_countries.geojson"]:
    step(n, lambda n=n: ne(n))
U = "https://earthquake.usgs.gov/fdsnws/event/1/"
def counts(minmag, extra, years):
    res = {}
    for y in years:
        p = {"starttime": f"{y}-01-01", "endtime": f"{y+1}-01-01", "minmagnitude": minmag, **extra}
        res[y] = requests.get(U + "count", params=p, timeout=60).text.strip()
    return res
step("global_m45_count", lambda: counts(4.5, {}, range(2016, 2026)))
step("global_m25_count", lambda: counts(2.5, {}, [2024, 2025]))
step("conus_m25_count", lambda: counts(2.5, {"minlatitude": 24, "maxlatitude": 50, "minlongitude": -125, "maxlongitude": -66}, [2024, 2025]))
step("alaska_m25_count", lambda: counts(2.5, {"minlatitude": 50, "maxlatitude": 72, "minlongitude": -180, "maxlongitude": -129}, [2024, 2025]))
def recent():
    r = requests.get(U + "query", params={"format": "geojson", "starttime": "2026-09-02", "minmagnitude": 1.5, "limit": 20000}, timeout=120).json()
    f = r["features"]; p0 = f[0]["properties"]
    tails = collections.Counter((x["properties"].get("place") or "").split(",")[-1].strip() for x in f)
    nets = collections.Counter(x["properties"].get("net") for x in f)
    big = [ {k: x["properties"].get(k) for k in ("mag","place","alert","tsunami","felt","sig","mmi","cdi","magType","net")} for x in f if (x["properties"].get("mag") or 0) >= 6]
    return {"n": len(f), "prop_keys": sorted(p0), "tails_top": tails.most_common(120), "nets": nets.most_common(20), "big": big,
            "noplace": sum(1 for x in f if not x["properties"].get("place"))}
step("recent", recent)
def mags_outside_us():
    r = requests.get(U + "query", params={"format": "geojson", "starttime": "2026-09-02", "minmagnitude": 1.5, "limit": 20000}, timeout=120).json()
    h = collections.Counter()
    for x in r["features"]:
        lon, lat = x["geometry"]["coordinates"][:2]
        us = (24 < lat < 50 and -125 < lon < -66) or (50 < lat < 72 and (lon < -129 or lon > 170)) or (18 < lat < 23 and -161 < lon < -154) or (17 < lat < 19.5 and -68 < lon < -65)
        m = x["properties"]["mag"] or 0
        h[("us" if us else "other", int(m*2)/2)] += 1
    return sorted([[k[0], k[1], v] for k, v in h.items()])
step("mag_hist", mags_outside_us)
json.dump(out, open("tools/probe_out.json", "w"), indent=1, default=str)
