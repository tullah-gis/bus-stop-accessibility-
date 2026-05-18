from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import stops

app = FastAPI(
    title="Bus Stop Accessibility API",
    description="Spatial API for bus stop coverage analysis in Frankfurt",
    version="1.0.0"
)

# CORS damit das Frontend die API aufrufen kann
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stops.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Bus Stop Accessibility API", "docs": "/docs"}
