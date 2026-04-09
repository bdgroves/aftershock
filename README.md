# AFTERSHOCK
### *Real-Time U.S. Seismic Activity Monitor*

---

> *"The fault does not forgive. The data never lies."*

[![Seismic Update](https://github.com/bdgroves/aftershock/actions/workflows/update.yml/badge.svg)](https://github.com/bdgroves/aftershock/actions/workflows/update.yml)
![Data](https://img.shields.io/badge/data-USGS%20Earthquake%20Hazards%20Program-e63946)
![Updates](https://img.shields.io/badge/updates-every%206%20hours-2ec4b6)
![Threshold](https://img.shields.io/badge/threshold-M%201.5%2B-f4a261)

**[→ Live Dashboard — brooksgroves.com/aftershock](https://brooksgroves.com/aftershock)**

---

## The Ground Beneath Your Feet

I grew up in Sonora, California — a Gold Rush town wedged into the western Sierra Nevada foothills of Tuolumne County, where the hills are crumpled and old and full of stories the rocks don't easily give up. The Melones Fault Zone runs right through that country. As a kid, I walked those fault scarps without knowing what they were. I just knew the land felt different there — broken in some deep, geological way, like the earth was remembering something.

The 1989 Loma Prieta earthquake hit when I was young. I remember what it felt like when the ground — the thing you spend your entire life trusting completely — decided for a few seconds that it was done being trusted.

AFTERSHOCK is that memory grown up and given a dashboard.

---

## What It Does

Every six hours, a GitHub Actions pipeline wakes up, calls the **USGS Earthquake Hazards Program ComCat API**, and pulls every measurable shake across the United States and beyond — magnitude 1.5 and up, worldwide. It writes a static JSON file. A dark, cinematic map loads it. The earth speaks. You listen.

---

## Dashboard

### The Map
A full world map on ESRI Dark Gray Canvas tiles. Earthquake dots are sized and colored by magnitude — tiny green pinpoints for the microseismicity, climbing through yellow, orange, red, and into deep red and purple as the energy scales up. A magnitude 7 sits on the map like a bruise.

Click any dot. A popup opens with the magnitude, location, depth, time elapsed, and a direct link to the USGS event page. Every dot. Every earthquake.

### State Deep-Dives
Click any US state — active or quiet. Active states light up in red on the choropleth. Quiet ones are cool blue. Click either way and you get a full breakdown:

- Event count for your current filter window
- Largest magnitude in the past 30 days and where it happened
- Average magnitude and average depth
- Depth classification (shallow vs. deep)
- Magnitude distribution bar chart
- Most recent events list, sorted newest first, each with a USGS event link

Quiet states get a different message: *"Quiet is not nothing — it may mean the fault is locked."*

### National Overview
The leaderboard. Top states ranked by event count, color-coded by intensity. Alaska is always first. It is not even close.

### Filters
Two controls that wire through everything simultaneously:

- **Time Window** — 1D / 3D / 7D / 14D / 30D buttons. Change the window; the map, the state panel, and the recent list all update instantly.
- **Magnitude Slider** — drag from M1.5 up to M6.0. Watch the noise disappear. Watch the significant events remain.

### Hiroshima Equivalent
Total seismic energy released in the dataset, expressed as a multiple of the Hiroshima atomic bomb yield (~6.3 × 10¹³ joules). Because "1.8 × 10¹⁷ joules" means nothing until you say it a different way.

---

## Architecture

```
USGS Earthquake Hazards Program ComCat API
              │
              │  Python / requests — every 6 hours
              ▼
      fetch/fetch_quakes.py
              │
              │  static JSON committed to repo
              ▼
       data/earthquakes.json
              │
              │  Leaflet.js + Chart.js — no build step
              ▼
          index.html  →  brooksgroves.com/aftershock
```

One Python script. One JSON file. Zero databases. Zero servers. The whole pipeline is auditable in an afternoon.

---

## Stack

| Component        | Technology |
|------------------|-----------|
| Data fetch       | Python 3.11 / requests |
| Environment      | [pixi](https://prefix.dev/) |
| Automation       | GitHub Actions (every 6 hours) |
| Map tiles        | ESRI Dark Gray Canvas (free, no key) |
| State boundaries | PublicaMundi US GeoJSON via CDN |
| Map engine       | Leaflet.js |
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

| Magnitude | Energy equivalent |
|-----------|-----------------|
| M 2.0 | Small construction blast |
| M 4.0 | ~1 ton of TNT |
| M 5.0 | ~32 tons of TNT |
| M 6.0 | Hiroshima bomb |
| M 7.0 | 32 Hiroshima bombs |
| M 8.0 | 1,000 Hiroshima bombs |
| M 9.0 | 32,000 Hiroshima bombs |

Each full magnitude step releases ~31.6× more energy than the step below it. The Richter scale is not intuitive. AFTERSHOCK tries to make it so.

---

## Related Projects

| Project | Description |
|---------|-------------|
| **[PELE](https://brooksgroves.com)** | Kīlauea volcano dashboard — active episodic fountaining, built for a May 2026 birthday trip to Hawaiʻi Volcanoes National Park |
| **[Project Kiva](https://github.com/bdgroves/project-kiva)** | Southwest archaeology remote sensing using USGS 3DEP LiDAR |
| **[SIERRA-FLOW](https://bdgroves.github.io/sierra-streamflow)** | Sierra Nevada streamflow monitor — Tuolumne, Merced, Stanislaus watersheds |
| **[EDGAR](https://bdgroves.github.io/EDGAR)** | Early Data & Game Analytics Report — Seattle Mariners & Tacoma Rainiers |
| **[Rainier Snowpack](https://bdgroves.github.io)** | Glacial water equivalent tracking on Mount Rainier |

---

## Fine Print

Seismic data sourced from the [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/) ComCat API. Small events below M2.0 may be underreported in lightly instrumented regions. State attribution is parsed from USGS place strings; offshore and territorial events may not map to a US state.

The automatic update commits read: `🌍 Seismic update: YYYY-MM-DD HH:MM UTC`. When you see those appearing in the commit history, the pipeline is healthy.

---

*Built by someone who grew up walking fault scarps without knowing it.*  
*Data: [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/)*
