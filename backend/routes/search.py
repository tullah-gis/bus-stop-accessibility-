"""
Network-based accessibility search endpoint.
Uses cached pedestrian street network for fast repeated queries.
"""

from fastapi import APIRouter
import osmnx as ox
import networkx as nx
from shapely.geometry import mapping, MultiPoint
from sqlalchemy import text
from backend.database import engine

router = APIRouter()

# Cache — Straßennetz wird einmal geladen und wiederverwendet
_graph_cache = {}

def get_graph(lat, lon, dist):
    """Lädt Straßennetz und cached es nach Gebiet."""
    # Runde auf 2 Dezimalstellen → gleiche Gegend = gleicher Cache
    key = (round(lat, 2), round(lon, 2), dist)
    if key not in _graph_cache:
        print(f"[Cache MISS] Lade Straßennetz für {key}")
        _graph_cache[key] = ox.graph_from_point(
            (lat, lon),
            dist=dist + 300,
            network_type="walk",
            simplify=True
        )
    else:
        print(f"[Cache HIT] Nutze gecachtes Netz für {key}")
    return _graph_cache[key]


@router.get("/search")
def search_stops(address: str, radius: int = 300):
    """
    Find bus stops reachable within walking distance from an address.
    Uses actual pedestrian street network + in-memory graph cache.
    """

    # 1. Geocode
    try:
        location = ox.geocode(address)
        lat, lon = location[0], location[1]
    except Exception as e:
        return {"error": f"Address not found: {str(e)}"}

    # 2. Straßennetz laden (gecacht)
    try:
        G = get_graph(lat, lon, radius)
    except Exception as e:
        return {"error": f"Could not load street network: {str(e)}"}

    # 3. Nächster Knoten zum Suchpunkt
    origin_node = ox.nearest_nodes(G, lon, lat)

    # 4. Erreichbare Knoten berechnen
    reachable_nodes = nx.single_source_dijkstra_path_length(
        G, origin_node, cutoff=radius, weight="length"
    )

    if not reachable_nodes:
        return {"error": "No reachable nodes found"}

    # 5. Bounding Box der erreichbaren Knoten
    lons = [G.nodes[n]["x"] for n in reachable_nodes]
    lats = [G.nodes[n]["y"] for n in reachable_nodes]
    bbox_sql = f"ST_MakeEnvelope({min(lons)}, {min(lats)}, {max(lons)}, {max(lats)}, 4326)"

    # 6. Haltestellen aus PostGIS laden
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

    # 7. Nur tatsächlich erreichbare Stops behalten
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

    reachable_stops.sort(key=lambda x: x["distance_m"])

    # 8. Isochrone
    points = MultiPoint([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in reachable_nodes])
    isochrone = mapping(points.convex_hull) if len(reachable_nodes) >= 3 else None

    return {
        "search_point": {"lat": lat, "lon": lon},
        "radius_m": radius,
        "stops_found": len(reachable_stops),
        "stops": reachable_stops,
        "isochrone": isochrone
    }
