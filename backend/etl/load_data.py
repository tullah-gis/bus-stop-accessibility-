"""
ETL Pipeline: OpenStreetMap Bus Stops → PostGIS
Lädt alle Bushaltestellen für Frankfurt am Main.
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from backend.database import engine

def load_bus_stops():
    print("[ETL] Lade alle Bushaltestellen für Frankfurt am Main ...")

    tags = {"highway": "bus_stop"}
    gdf = ox.features_from_place("Frankfurt am Main, Germany", tags=tags)
    gdf = gdf[gdf.geometry.geom_type == "Point"].copy()
    gdf = gdf.reset_index()
    gdf["osm_id"] = gdf["id"].astype(str)
    gdf["name"] = gdf["name"] if "name" in gdf.columns else None
    gdf = gdf[["osm_id", "name", "geometry"]]
    gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.drop_duplicates(subset="osm_id")

    print(f"      → {len(gdf)} Haltestellen gefunden")

    print("[ETL] Speichere in Supabase/PostGIS ...")
    gdf.to_postgis(
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

    print(f"✓ Fertig — {len(gdf)} Haltestellen geladen.")
    return len(gdf)

if __name__ == "__main__":
    load_bus_stops()
