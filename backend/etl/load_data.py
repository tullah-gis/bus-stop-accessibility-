"""
ETL Pipeline: OpenStreetMap Bus Stops → PostGIS
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from backend.database import engine

DISTRICTS = [
    "Bockenheim, Frankfurt am Main, Germany",
    "Nordend-West, Frankfurt am Main, Germany",
    "Nordend-Ost, Frankfurt am Main, Germany",
    "Westend-Nord, Frankfurt am Main, Germany",
    "Westend-Süd, Frankfurt am Main, Germany",
    "Ostend, Frankfurt am Main, Germany",
]

def load_bus_stops():
    all_stops = []

    for district in DISTRICTS:
        print(f"[ETL] Lade Bushaltestellen für: {district}")
        try:
            tags = {"highway": "bus_stop"}
            gdf = ox.features_from_place(district, tags=tags)
            gdf = gdf[gdf.geometry.geom_type == "Point"].copy()
            gdf = gdf.reset_index()
            gdf["osm_id"] = gdf["id"].astype(str)
            gdf["name"] = gdf["name"] if "name" in gdf.columns else None
            gdf["district"] = district.split(",")[0]
            gdf = gdf[["osm_id", "name", "district", "geometry"]]
            all_stops.append(gdf)
            print(f"      → {len(gdf)} Haltestellen gefunden")
        except Exception as e:
            print(f"      ✗ Fehler: {e}")

    if not all_stops:
        print("Keine Daten geladen!")
        return 0

    combined = pd.concat(all_stops, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")
    combined = combined.drop_duplicates(subset="osm_id")

    print(f"\n[ETL] Speichere {len(combined)} Haltestellen in PostGIS ...")
    combined.to_postgis(
        name="bus_stops",
        con=engine,
        if_exists="replace",
        index=False,
    )

    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS bus_stops_geom_idx "
            "ON bus_stops USING GIST(geometry);"
        ))
        conn.commit()

    print(f"✓ Fertig — {len(combined)} Haltestellen geladen.")
    return len(combined)


def load_districts():
    all_districts = []

    for district in DISTRICTS:
        print(f"[ETL] Lade Stadtgrenze: {district}")
        try:
            gdf = ox.geocode_to_gdf(district)
            gdf["district"] = district.split(",")[0]
            gdf = gdf[["district", "geometry"]]
            all_districts.append(gdf)
        except Exception as e:
            print(f"      ✗ Fehler: {e}")

    combined = pd.concat(all_districts, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")

    print(f"\n[ETL] Speichere {len(combined)} Stadtgrenzen in PostGIS ...")
    combined.to_postgis(
        name="districts",
        con=engine,
        if_exists="replace",
        index=False,
    )
    print(f"✓ {len(combined)} Stadtgrenzen geladen.")


if __name__ == "__main__":
    load_bus_stops()
    load_districts()
