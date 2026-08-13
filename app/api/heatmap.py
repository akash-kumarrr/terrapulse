#extract data for heatmap

from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Annotated
from redis.asyncio import Redis
from app.services.cache import get_or_set_cache
from app.core.redis import get_redis
from app.services.geodata_extractor import extract_city_environmental_data, CityDataRequest
from app.core.config import settings

router = APIRouter(
    prefix="/heatmap",
    tags=['heatmap-data']
)

@router.post('/heatmap_data')
async def fetch_heatmap_data(
    city: Annotated[str | None, Query()] = "delhi", 
    state : Annotated[str | None, Query()] = "delhi",
    redis : Redis = Depends(get_redis)
):
    try:
        query_key = f"{city}_{state}"
        city_red_data_model = CityDataRequest(
            city=city,
            state=state,
            gcp_project_id=settings.gee_project_id,
        )
        data = await get_or_set_cache(
            redis=redis,
            key=query_key,
            fetch_func=lambda : extract_city_environmental_data(city_red_data_model),
            ttl=86600
        )
        return {
            "data" : data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        raise


        


