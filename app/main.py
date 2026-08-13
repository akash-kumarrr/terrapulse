from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.heatmap import router as heatmap_data_router
from app.core.config import settings
from app.core.redis import init_redis, close_redis, get_redis
from contextlib import asynccontextmanager
from app.api.model import router as prediction_model_router



@asynccontextmanager
async def lifespan(app : FastAPI):
    await init_redis()
    yield
    await close_redis()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

@app.get("/")
async def root() :
    return {
        "title" : settings.app_name,
        "status" : "online"
    }
app.include_router(health_router)
app.include_router(heatmap_data_router)
app.include_router(prediction_model_router)