from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
import json

router = APIRouter()

@router.get("/stops")
def get_stops(district: str = None, db: Session = Depends(get_db)):
    """Alle Bushaltestellen als GeoJSON."""
    if district:
        sql = text("""
            SELECT osm_id, name, district,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM bus_stops
            WHERE district = :district
        """)
        rows = db.execute(sql, {"district": district}).fetchall()
    else:
        sql = text("""
            SELECT osm_id, name, district,
                   ST_AsGeoJSON(geometry)::json AS geometry
            FROM bus_stops
        """)
        rows = db.execute(sql).fetchall()

    features = [
        {
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {
                "osm_id": row.osm_id,
                "name": row.name,
                "district": row.district,
            }
        }
        for row in rows
    ]

    return {"type": "FeatureCollection", "features": features}


@router.get("/coverage")
def get_coverage(radius: int = 300, db: Session = Depends(get_db)):
    """Versorgungsfläche — Union aller Haltestellen-Umkreise."""
    sql = text("""
        SELECT ST_AsGeoJSON(
            ST_Union(
                ST_Buffer(geometry::geography, :radius)::geometry
            )
        )::json AS coverage
        FROM bus_stops
    """)
    result = db.execute(sql, {"radius": radius}).fetchone()
    return {
        "type": "Feature",
        "geometry": result.coverage,
        "properties": {"radius_m": radius}
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Statistiken pro Stadtteil."""
    sql = text("""
        SELECT district,
               COUNT(*) AS stop_count
        FROM bus_stops
        GROUP BY district
        ORDER BY stop_count DESC
    """)
    rows = db.execute(sql).fetchall()
    return [{"district": r.district, "stop_count": r.stop_count} for r in rows]


@router.get("/gaps")
def get_gaps(radius: int = 300, db: Session = Depends(get_db)):
    """Gebiete ohne Busversorgung innerhalb der Stadtteile."""
    sql = text("""
        WITH district_boundary AS (
            SELECT ST_Union(geometry) AS geom
            FROM districts
        ),
        coverage AS (
            SELECT ST_Union(
                ST_Buffer(geometry::geography, :radius)::geometry
            ) AS geom
            FROM bus_stops
        )
        SELECT ST_AsGeoJSON(
            ST_Difference(d.geom, c.geom)
        )::json AS gaps
        FROM district_boundary d, coverage c
    """)
    result = db.execute(sql, {"radius": radius}).fetchone()
    return {
        "type": "Feature",
        "geometry": result.gaps,
        "properties": {"radius_m": radius, "description": "Areas without bus coverage"}
    }
