from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from backend.database import Base

class BusStop(Base):
    __tablename__ = "bus_stops"

    id       = Column(Integer, primary_key=True, index=True)
    osm_id   = Column(String, unique=True)
    name     = Column(String, nullable=True)
    geom     = Column(Geometry(geometry_type="POINT", srid=4326))

class CoverageGap(Base):
    __tablename__ = "coverage_gaps"

    id       = Column(Integer, primary_key=True, index=True)
    district = Column(String, nullable=True)
    geom     = Column(Geometry(geometry_type="POLYGON", srid=4326))
    gap_area = Column(Float)
