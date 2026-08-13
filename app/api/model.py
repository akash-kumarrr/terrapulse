from typing import Annotated
from fastapi import APIRouter, Query, Body, HTTPException, status
from app.core.config import settings
from app.schemas.environment_features import EnvironmentalFeatures
from app.services.model import predict_lst_json

router = APIRouter(
    prefix="/model",
    tags=["model-prediction"]
)


@router.post("/predict_lst")
async def predict(
    environment_feature_payload: Annotated[EnvironmentalFeatures, Body()],
    city: Annotated[str | None, Query()] = "delhi",
    state: Annotated[str | None, Query()] = "delhi",
    gee_project_id: Annotated[str | None, Query()] = settings.gee_project_id,
):
    try:
        data = predict_lst_json(environment_feature_payload)
        return {
            "city": city,
            "state": state,
            "gee_project_id": gee_project_id,
            "result": data
        }
    except HTTPException:
        # Re-raise any FastAPI HTTP exceptions explicitly
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )