import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly pre-warm vector store and embeddings on startup so first user requests are fast
    try:
        from app.api.routes import get_workflow
        get_workflow()
    except Exception as e:
        logger.warning(f"Startup workflow warmup note: {e}")
    yield

def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application."""
    app = FastAPI(
        title="Campus/Facility Infrastructure Decision-Support API",
        description="RESTful API for campus maintenance retrieval, diagnosis, recommendations, and technician feedback loop.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Base CORS origins for local frontend development
    origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Incorporate deployed cloud frontend origin(s) (e.g. Vercel deployment URL)
    frontend_origins_env = os.getenv("FRONTEND_ORIGIN", "")
    if frontend_origins_env:
        for item in frontend_origins_env.split(","):
            cleaned = item.strip().rstrip("/")
            if cleaned and cleaned not in origins:
                origins.append(cleaned)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app

app = create_app()
