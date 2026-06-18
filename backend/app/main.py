from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api as api_v1
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Virtual Pal Backend - Learning CI/CD, Docker & Redis",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": f"{settings.PROJECT_NAME} API is running"}
