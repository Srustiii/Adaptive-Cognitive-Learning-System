import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.admin import router as admin_router
from app.database import SessionLocal, init_db
from app.question_bank import ensure_sample_datasets, seed_questions_from_csv
from app.routes import router

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SIMULATION_RESULTS_DIR = BASE_DIR.parent / "simulation_results"

app = FastAPI(
    title="Adaptive Cognitive Learning System",
    description="Lightweight research-oriented backend for adaptive learning experiments.",
    version="0.1.0",
)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount(
    "/simulation-results",
    StaticFiles(directory=SIMULATION_RESULTS_DIR, check_dir=False),
    name="simulation_results",
)


@app.on_event("startup")
def on_startup():
    """Initialize SQLite tables and seed internal datasets before serving requests."""
    init_db()
    ensure_sample_datasets()
    db = SessionLocal()
    try:
        seed_questions_from_csv(db)
    finally:
        db.close()
    port = os.getenv("PORT", "8021")
    print("--------------------------------")
    print("AdaptiveLearn AI running")
    print("Student UI:")
    print(f"http://127.0.0.1:{port}")
    print("")
    print("Admin Panel:")
    print(f"http://127.0.0.1:{port}/admin/login")
    print("--------------------------------")


@app.get("/", include_in_schema=False)
def landing_page():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/ui", include_in_schema=False)
def old_frontend():
    return RedirectResponse("/")


# Routes are kept in one simple module to stay beginner-friendly.
app.include_router(admin_router)
app.include_router(router)


@app.get("/app/{page_name}", include_in_schema=False)
def app_page(page_name: str):
    """Serve lightweight multi-page frontend routes under /app."""
    allowed_pages = {"register", "login", "dashboard", "quiz", "coding", "progress", "settings", "course"}
    if page_name in allowed_pages:
        return FileResponse(STATIC_DIR / f"{page_name}.html")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{page_name}", include_in_schema=False)
def app_page(page_name: str):
    """Serve lightweight multi-page frontend routes."""
    allowed_pages = {"register", "login", "dashboard", "quiz", "coding", "progress", "settings", "course"}
    if page_name in allowed_pages:
        return FileResponse(STATIC_DIR / f"{page_name}.html")
    return FileResponse(STATIC_DIR / "index.html")
