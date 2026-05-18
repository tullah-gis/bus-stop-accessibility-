# Bus Stop Accessibility Analyzer

A full-stack geospatial web application that analyzes public bus stop coverage in Frankfurt am Main using real OpenStreetMap data, PostGIS spatial queries, and an interactive Leaflet map.

![Dashboard Preview](img/bus-access.png)

---

## Motivation

Urban mobility planning depends on understanding how well neighborhoods are served by public transport. This tool automatically identifies coverage gaps — areas where residents live more than 300m from the nearest bus stop — directly applicable to smart city, urban planning, and mobility GIS workflows.

---

## Features

- Automated OSM data retrieval for bus stops and district boundaries
- 300m coverage buffer analysis per stop using PostGIS geography functions
- Coverage gap detection via `ST_Difference` between district boundaries and coverage area
- REST API serving GeoJSON endpoints with FastAPI
- Interactive Leaflet map with layer toggles and district filtering
- Fully containerized PostGIS database via Docker
- Reproducible environment via conda

---

## Tech Stack

| Layer | Tool |
|---|---|
| Database | PostgreSQL + PostGIS (Docker) |
| ETL | osmnx · GeoPandas · Python |
| API | FastAPI · GeoAlchemy2 · SQLAlchemy |
| Frontend | Leaflet.js · HTML/CSS |
| Environment | conda · Docker Compose |

---

## Architecture

```
OpenStreetMap (OSM)
        ↓
ETL Pipeline (osmnx + GeoPandas)
        ↓
PostGIS Database (Docker)
        ↓
FastAPI REST API
        ↓
Leaflet Frontend (Browser)
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/stops` | All bus stops as GeoJSON |
| `GET /api/stops?district=Bockenheim` | Filtered by district |
| `GET /api/coverage?radius=300` | Union of all stop buffers |
| `GET /api/gaps?radius=300` | Areas without bus coverage |
| `GET /api/stats` | Stop count per district |

Interactive API docs available at `http://localhost:8000/docs`

---

## Coverage Analysis

For each bus stop a 300m buffer is calculated using PostGIS geography functions. The coverage gap is the spatial difference between the real district boundaries (from OSM) and the union of all coverage areas:

```sql
ST_Difference(district_boundary, ST_Union(ST_Buffer(geometry::geography, 300)))
```

Red areas on the map indicate zones where residents are more than 300m from any bus stop.

---

## Districts Covered

- Bockenheim
- Nordend-West
- Nordend-Ost
- Westend-Nord
- Westend-Süd
- Ostend

---

## Installation

### Requirements

- Docker
- conda

### Setup

```bash
git clone https://github.com/tullah-gis/bus-stop-accessibility.git
cd bus-stop-accessibility

# Start PostGIS
docker compose up -d

# Create environment
conda env create -f environment.yml
conda activate bus-accessibility

# Load OSM data into PostGIS
python -m backend.etl.load_data

# Start API
uvicorn backend.main:app --reload
```

Open `frontend/index.html` in your browser.

API docs: `http://localhost:8000/docs`

---

## Project Structure

```
bus-stop-accessibility/
├── docker-compose.yml
├── requirements.txt
├── environment.yml
├── backend/
│   ├── main.py          # FastAPI app
│   ├── database.py      # DB connection
│   ├── models.py        # Table definitions
│   ├── routes/
│   │   └── stops.py     # API endpoints
│   └── etl/
│       └── load_data.py # OSM → PostGIS pipeline
├── frontend/
│   └── index.html       # Leaflet map
└── img/
    └── bus-access.png
```

---

## Author

**Tahira Ullah** — Geoinformatikerin
MSc Geography (Geoinformatics), Ruprecht-Karls-Universität Heidelberg
📧 tahira.ullah@hotmail.de
🌍 Frankfurt am Main, Germany

---

## License

MIT License — free to use, modify, and distribute with attribution.

*Data © OpenStreetMap contributors — [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright)*
