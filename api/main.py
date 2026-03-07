"""FastAPI application — LogisticsMind AI API."""
import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("logisticsmind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LogisticsMind AI API starting...")
    yield
    logger.info("LogisticsMind AI API shutting down...")


app = FastAPI(
    title="LogisticsMind AI",
    description="Conversational AI analytics for CeyLog logistics",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(health.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} — {response.status_code} ({elapsed:.2f}s)")
    return response
