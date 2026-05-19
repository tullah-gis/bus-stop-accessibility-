"""
Network-based accessibility search endpoint.
Geocodes an address and finds bus stops within walking distance
using the actual pedestrian street network.
"""

from fastapi import APIRouter
import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import mapping
from sqlalchemy import text
from backend.database import engine
import json

router = APIRouter()

@router.get("/search")
def search_stops(address: str, radius: int = 300):
    """
    Find bus stops reachable within walking distance from an address.
    Uses actual pedestrian street network, not simple buffers.
    
    - address: e.g. "Zeil 1, Frankfurt am Main"
    - radius: walking distance in meters (default 300m)
    """

    # 1. Geocode address → coordinates
    try:
        location = ox.geocode(address)
        lat, lon = location[0], location[1]
    except Exception as e:
        return {"error": f"Address not found: {str(e)}"}

    # 2. Load pedestrian street network around the point
    try:
        G = ox.graph_from_point(
            (lat, lon),
            dist=radius + 200,  # etwas größer für Puffer
            network_type="walk",
            simplify=True
        )
    except Exception as e:
        return {"error": f"Could not load street network: {str(e)}"}

    # 3. Find nearest node to the search point
    origin_node = ox.nearest_nodes(G, lon, lat)

    # 4. Calculate all nodes reachable within radius (meters)
    reachable_nodes = nx.single_source_dijkstra_path_length(
        G, origin_node, cutoff=radius, weight="length"
    )

    # 5. Get coordinates of reachable nodes
    reachable_coords = [
        (G.nodes[n]["x"], G.nodes[n]["y"])
        for n in reachable_nodes
    ]

    if not reachable_coords:
        return {"error": "No reachable nodes found"}

    # 6. Build bounding box from reachable nodes
    lons = [c[0] for c in reachable_coords]
    lats = [c[1] for c in reachable_coords]
    bbox_sql = f"ST_MakeEnvelope({min(lons)}, {min(lats)}, {max(lons)}, {max(lats)}, 4326)"

    # 7. Query bus stops from PostGIS within bounding box
    sql = text(f"""
        SELECT osm_id, name,
               ST_X(geometry) as lon,
               ST_Y(geometry) as lat,
               ST_AsGeoJSON(geometry)::json as geometry
        FROM bus_stops
        WHERE ST_Within(geometry, {bbox_sql})
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()

    # 8. Filter stops that are actually reachable via network
    reachable_stops = []
    for row in rows:
        stop_node = ox.nearest_nodes(G, row.lon, row.lat)
        try:
            dist = nx.shortest_path_length(
                G, origin_node, stop_node, weight="length"
            )
            if dist <= radius:
                reachable_stops.append({
                    "osm_id": row.osm_id,
                    "name": row.name or "Unnamed Stop",
                    "distance_m": round(dist),
                    "geometry": row.geometry
                })
        except nx.NetworkXNoPath:
            continue

    # 9. Sort by distance
    reachable_stops.sort(key=lambda x: x["distance_m"])

    # 10. Build isochrone polygon from reachable nodes
    node_points = [
        {"x": G.nodes[n]["x"], "y": G.nodes[n]["y"]}
        for n in reachable_nodes
    ]

    # Convex hull of reachable nodes as isochrone
    from shapely.geometry import MultiPoint
    if len(node_points) >= 3:
        points = MultiPoint([(p["x"], p["y"]) for p in node_points])
        isochrone = mapping(points.convex_hull)
    else:
        isochrone = None

    return {
        "search_point": {"lat": lat, "lon": lon},
        "radius_m": radius,
        "stops_found": len(reachable_stops),
        "stops": reachable_stops,
        "isochrone": isochrone
    }
