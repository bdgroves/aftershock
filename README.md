# AFTERSHOCK
### *Real-Time U.S. Seismic Activity Monitor*

---

> *"The fault does not forgive. The data never lies."*

[![Seismic Update](https://github.com/bdgroves/aftershock/actions/workflows/update.yml/badge.svg)](https://github.com/bdgroves/aftershock/actions/workflows/update.yml)
![Data](https://img.shields.io/badge/data-USGS%20Earthquake%20Hazards%20Program-e63946)
![Update Frequency](https://img.shields.io/badge/updates-every%206%20hours-2ec4b6)
![Min Magnitude](https://img.shields.io/badge/threshold-M%201.5%2B-f4a261)

**[→ Live Dashboard](https://bdgroves.github.io/aftershock)**

---

## The Ground Beneath Your Feet

I grew up in Sonora, California — a Gold Rush town wedged into the western Sierra Nevada foothills of Tuolumne County, where the hills are crumpled and old and full of stories the rocks don't easily give up. The Melones Fault Zone runs right through that country. As a kid, I walked those fault scarps without knowing what they were. I just knew the land felt different there — broken in some deep, geological way, like the earth was remembering something.

The 1989 Loma Prieta earthquake hit when I was young. I remember the feeling. The ground, which you spend your whole life trusting completely, decided for a few seconds that it was done being trusted.

AFTERSHOCK is that memory grown up and given a dashboard.

---

## What It Does

AFTERSHOCK pulls live earthquake data from the **USGS Earthquake Hazards Program** every six hours — every measurable shake, rattle, and rupture across the United States — and renders it as a dark, interactive seismic monitor. Click any state. Watch the numbers change. This is the planet, breathing.

### Dashboard Features

- **Live Choropleth Map** — US states shaded by seismic activity level, from quiet blues to alarm reds. At a glance, you know where the earth is restless.

- **Clickable State Deep-Dives** — Click any state for a full statistical breakdown: total event count, largest magnitude, average depth, magnitude distribution chart, depth classification (shallow / intermediate / deep), and a ranked list of the most significant recent events.

- **National Leaderboard** — The top active states ranked by event count, color-coded by intensity. Alaska is always winning this race. It is not even close.

- **Hiroshima Equivalent Energy** — Total seismic energy released in the past 30 days, expressed as a multiple of the Hiroshima atomic bomb yield (~6.3 × 10¹³ J). Because scale matters, and "1.8 × 10¹⁷ joules" means nothing until you say it differently.

- **Recent Significant Events** — A live-scrolling list of M3+ events in reverse chronological order. Click any event to fly the map to its epicenter.

- **Magnitude Filter** — Slide from M1.5 background microseismicity up through major events. Watch Alaska thin out. Watch California stay busy.

- **Automatic Updates** — GitHub Actions runs the Python fetch pipeline every 6 hours. The data is always within a few hours of current.

---

## Architecture

```
USGS Earthquake Hazards Program ComCat API
              │
              │  (Python / requests, every 6h)
              ▼
      fetch/fetch_quakes.py
              │
              │  (static JSON, committed to repo)
              ▼
       data/earthquakes.json
              │
              │  (Leaflet.js + Chart.js, no build step)
              ▼
          index.html
              │
              ▼
       GitHub Pages
```

The data pipeline is intentionally simple: one Python script, one JSON file, zero databases, zero servers. The entire dashboard runs as static files — the same architecture as every other project in this collection.

---

## The Numbers Behind the Numbers

| Magnitude | Energy equivalent |
|-----------|------------------|
| M2.0      | Small construction blast |
| M4.0      | ~1 ton of TNT |
| M5.0      | ~32 tons of TNT |
| M6.0      | Hiroshima bomb |
| M7.0      | 32 Hiroshima bombs |
| M8.0      | 1,000 Hiroshima bombs |
| M9.0      | 32,000 Hiroshima bombs |

Each full magnitude step releases **~31.6×** more energy than the one below it. This is why a M7 feels so different from a M6, even though the numbers look close. The Richter scale is not intuitive. AFTERSHOCK tries to make it so.

---

## Stack

| Component      | Technology |
|----------------|-----------|
| Data fetch     | Python 3.11 / requests |
| Automation     | GitHub Actions (cron: every 6h) |
| Map            | Leaflet.js + CartoDB Dark Matter tiles |
| State boundaries | PublicaMundi GeoJSON via CDN |
| Charts         | Chart.js |
| Frontend       | Vanilla HTML / CSS / JS — no frameworks |
| Hosting        | GitHub Pages |

---

## Local Development

```bash
git clone https://github.com/bdgroves/aftershock
cd aftershock
pip install requests
python fetch/fetch_quakes.py

# Then serve locally (required for Fetch API to work)
python -m http.server 8000
# → Open http://localhost:8000
```

---

## Related Projects

| Project | Description |
|---------|-------------|
| **[PELE](https://brooksgroves.com)** | Kīlauea volcano dashboard — active episodic fountaining, built ahead of a May 2026 birthday trip to Hawaiʻi Volcanoes National Park |
| **[Project Kiva](https://github.com/bdgroves/project-kiva)** | Southwest archaeology remote sensing using USGS 3DEP LiDAR |
| **[SIERRA-FLOW](https://bdgroves.github.io/sierra-streamflow)** | Sierra Nevada streamflow monitor — USGS gages on the Tuolumne, Merced, Stanislaus |
| **[EDGAR](https://bdgroves.github.io/EDGAR)** | Early Data & Game Analytics Report — Seattle Mariners & Tacoma Rainiers |
| **[Rainier Snowpack Monitor](https://bdgroves.github.io)** | Glacial water equivalent tracking on Mount Rainier |

---

## Fault Lines & Fine Print

Seismic data is sourced from the [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/) ComCat API and is subject to their data quality and completeness standards. Small events (M < 2.0) in lightly instrumented regions may be underreported. State attribution is parsed from USGS place strings and may miss some offshore or border events.

---

*Built by someone who grew up walking fault scarps without knowing it.*  
*Data: [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/)*
