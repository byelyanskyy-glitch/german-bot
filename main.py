from fastapi import FastAPI
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI successfully started")

@app.get("/")
async def root():
    return {
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "ok": True
    }
