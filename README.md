# AFTERSHOCK
### *Real-Time Earthquake Monitor — the United States first, and the world*

---

> *"The fault does not forgive. The data never lies."*

[![Seismic Update](https://github.com/bdgroves/aftershock/actions/workflows/update.yml/badge.svg)](https://github.com/bdgroves/aftershock/actions/workflows/update.yml)
![Data](https://img.shields.io/badge/data-USGS%20Earthquake%20Hazards%20Program-e63946)
![Updates](https://img.shields.io/badge/updates-hourly%20%2B%20live%20feed-2ec4b6)
![Threshold](https://img.shields.io/badge/threshold-M%201.5%2B-f4a261)

**[→ Live Dashboard — brooksgroves.com/aftershock](https://brooksgroves.com/aftershock)**

---

## The Ground Beneath Your Feet

I grew up in Groveland, California — a Gold Rush town wedged into the western Sierra Nevada foothills of Tuolumne County, where the hills are crumpled and old and full of stories the rocks don't easily give up. The Melones Fault Zone runs right through that country. As a kid, I walked those fault scarps without knowing what they were. I just knew the land felt different there — broken in some deep, geological way, like the earth was remembering something.

The 1989 Loma Prieta earthquake hit when I was young. I remember what it felt like when the ground — the thing you spend your entire life trusting completely — decided for a few seconds that it was done being trusted.

AFTERSHOCK is that memory grown up and given a dashboard.

---

## What It Does

Every hour, a GitHub Actions pipeline calls the **USGS ComCat API** for every earthquake of M1.5 and up in the last 30 days, worldwide, and works out where each one happened — which US state, which country, or which stretch of open ocean. It finds the aftershock sequences, and once a week it rebuilds ten years of history so every number can be read against normal. The page also reads the USGS real-time feed itself every two minutes, so a quake that happened five minutes ago is already on the map.

### Pick a place
The United States is the default. The picker covers every state and territory, every country with a quake this month, the world's regions, and the open ocean (mid-ocean ridges, trenches). Every view has its own link — `#us-CA`, `#cc-JP`, `#world`.

### Fair comparisons
ComCat is complete down to about **M1.5** where the US runs dense networks, but only to about **M4.5** for most of the world. Counting every M1.5 makes Alaska look like the busiest place on Earth — partly true, mostly seismometers. So "vs normal" and the rankings use **M2.5+ for US states** and **M4.5+ for countries**.

### Is this normal?
Daily counts against the ten-year average, and ten years of annual totals with this month's pace beside them. The baselines tell real stories: Oklahoma's wastewater-injection quakes rising and then collapsing after regulation (2,006 M2.5+ in 2016, 28 in 2025), West Texas rising the other way, Kīlauea in 2018, Ridgecrest in 2019, Puerto Rico in 2020.

### Aftershock sequences
Gardner–Knopoff space–time windows find each main shock and its aftershocks. For each sequence: the count, the largest aftershock against **Båth's law** (usually ~1.2 magnitudes smaller), the **Omori** decay exponent, and a flag when it behaves more like a **swarm** (fluids, magma, injection) than a main shock.

### The shape of the shaking
- **Gutenberg–Richter** magnitude–frequency plot with a maximum-likelihood **b-value** above the completeness magnitude
- **Energy** — where it went (the single largest quake usually carries most of it), in Hiroshima bombs or tons of TNT
- **Depth** — shallow crustal faulting vs. quakes inside sinking ocean slabs, down to ~700 km

### The map
Esri Dark Gray Canvas. Dots sized by magnitude and coloured by age (or by depth). Click any one for magnitude type, depth, felt reports, MMI, PAGER alert and the USGS event page. Quiet states still say: *"Quiet is not nothing — it may mean the fault is locked."*

---

## Architecture

```
USGS ComCat (FDSN event API)                 USGS real-time feed
        │  hourly, GitHub Actions                     │  every 2 min, in the browser
        ▼                                             │
fetch/fetch_quakes.py ── fetch/geo.py (point-in-polygon, offshore → nearest country)
        │                                             │
        ├─ data/earthquakes.json   30 days, compact columns, sequences
        ├─ data/baselines.json     10 years by country (M4.5+) and US state (M2.5+), weekly
        └─ data/geo/*.json         Natural Earth boundaries, committed once
        │                                             │
        └──────────────► index.html (Leaflet + Chart.js, no build step) ◄──┘
```

Commits happen every 6 hours, or straight away when a new M4.5+ arrives. A failing fetch keeps the published file and writes its error on the Actions run.

---

## Stack

| Component        | Technology |
|------------------|-----------|
| Data fetch       | Python 3.11 / requests — no GIS libraries |
| Environment      | [pixi](https://prefix.dev/) |
| Automation       | GitHub Actions (hourly) |
| Boundaries       | Natural Earth, simplified and committed |
| Map              | Leaflet.js on Esri Dark Gray Canvas |
| Charts           | Chart.js |
| Frontend         | Vanilla HTML / CSS / JS — no frameworks |
| Hosting          | brooksgroves.com (GitHub Pages) |

---

## Local Development

```bash
git clone https://github.com/bdgroves/aftershock
cd aftershock

# Install environment and run the data fetch
pixi run fetch

# Serve locally (required — fetch API won't work from file://)
pixi run serve
# → Open http://localhost:8000
```

---

## The Numbers

Energy from log₁₀E = 1.5M + 4.8 joules; one ton of TNT is 4.2 × 10⁹ J.

| Magnitude | Energy equivalent |
|-----------|-----------------|
| M 2.0 | ~15 kg of TNT |
| M 4.0 | ~15 tons of TNT |
| M 5.0 | ~480 tons of TNT |
| M 6.0 | ~1 Hiroshima bomb (15 kt) |
| M 7.0 | ~32 Hiroshima bombs |
| M 8.0 | ~1,000 Hiroshima bombs |
| M 9.0 | ~32,000 Hiroshima bombs |

Each whole magnitude step releases ~31.6× more energy than the one below it. *(Until October 2026 this table said M4 ≈ 1 ton and M5 ≈ 32 tons; both were about 15× too low.)*

---

## Related Projects

| Project | Description |
|---------|-------------|
| **[PELE](https://brooksgroves.com)** | Kīlauea volcano dashboard — active episodic fountaining, built for a May 2026 birthday trip to Hawaiʻi Volcanoes National Park |
| **[Project Kiva](https://github.com/bdgroves/project-kiva)** | Southwest archaeology remote sensing using USGS 3DEP LiDAR |
| **[SIERRA-FLOW](https://brooksgroves.com/sierra-streamflow/)** | Sierra Nevada streamflow monitor — Tuolumne, Merced, Stanislaus watersheds |
| **[EDGAR](https://bdgroves.github.io/EDGAR)** | Early Data & Game Analytics Report — Seattle Mariners & Tacoma Rainiers |
| **[Rainier Snowpack](https://brooksgroves.com/rainier-snowpack/)** | Mount Rainier snowpack against normal, 40+ winters and El Niño |

---

## Fine Print

Seismic data sourced from the [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/) ComCat API. Outside the US, events below about M4.5 are only patchily reported, which is why comparisons use M4.5+. Places are assigned from coordinates (Natural Earth polygons); offshore quakes go to the nearest country within 250 km (US states within 200 km), and anything further out is open ocean.

The automatic update commits read: `🌍 Seismic update: YYYY-MM-DD HH:MM UTC`. When you see those appearing in the commit history, the pipeline is healthy.

---

*Built by someone who grew up walking fault scarps without knowing it.*  
*Data: [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/)*
