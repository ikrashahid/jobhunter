import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import require_api_key
from api.routes import analyze, email_alert, matches, metrics, pdf, stats, trigger

app = FastAPI(title="Job Copilot API", version="1.0.0")

# Browsers should not call this API directly — the Next.js server proxies
# with the shared secret. CORS is pinned for local debugging / explicit
# allowlist only. No wildcard *.vercel.app.
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

_protected = [Depends(require_api_key)]

app.include_router(stats.router, prefix="/api", dependencies=_protected)
app.include_router(matches.router, prefix="/api", dependencies=_protected)
app.include_router(analyze.router, prefix="/api", dependencies=_protected)
app.include_router(metrics.router, prefix="/api", dependencies=_protected)
app.include_router(pdf.router, prefix="/api", dependencies=_protected)
app.include_router(trigger.router, prefix="/api", dependencies=_protected)
app.include_router(email_alert.router, prefix="/api", dependencies=_protected)


@app.get("/")
async def root():
    return {"status": "ok", "service": "Job Copilot API"}


@app.get("/health")
async def health():
    """Unauthenticated — Railway / uptime checks only. No data."""
    return {"status": "healthy"}