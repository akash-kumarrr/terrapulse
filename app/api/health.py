from fastapi import APIRouter, HTTPException, status

router = APIRouter(
    prefix="/health",
    tags=['health']
)

@router.get("/status")
async def get_health_status():
    return {
        "message" : "good"
    }

