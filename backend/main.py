from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routes import stops, search

app = FastAPI(
    title="Bus Stop Accessibility API",
    description="Spatial API for bus stop coverage analysis in Frankfurt",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stops.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
@app.head("/")
def root():
    return FileResponse("frontend/index.html")
