from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.calendar import router as calendar_router
from app.api.canvas import router as canvas_router
from app.api.demo import router as demo_router
from app.api.events import router as events_router
from app.api.google import router as google_router
from app.api.sources import router as sources_router
from app.api.gmail import router as gmail_router
from app.api.jobs import router as jobs_router


app = FastAPI(
    title="DueScope API",
    version="0.3.0",
    description="Evidence-backed academic deadline management for HackRice 16.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://due-scope-hack-rice.vercel.app",
        "https://due-scope-hack-rice-git-main-dong-quan-tran.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(demo_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(canvas_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(google_router, prefix="/api")
app.include_router(gmail_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "duescope-api"}
