from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import stats, matches, analyze, metrics, pdf, trigger

app = FastAPI(title="Job Copilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(pdf.router, prefix="/api")
app.include_router(trigger.router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok", "service": "Job Copilot API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
