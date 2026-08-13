import os
import json
from typing import Optional
import numpy as np
import pandas as pd
import xgboost as xgb
from app.schemas.environment_features import EnvironmentalFeatures
from pydantic import BaseModel, Field

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

# Point directly to ml_models/delhi_lst_environmental_model.json
MODEL_PATH = os.path.join(PROJECT_ROOT, "ml_models", "delhi_lst_environmental_model.json")


if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model file not found at: {os.path.abspath(MODEL_PATH)}\n"
        f"Please verify that 'mlmodel' directory exists in the parent folder."
    )

model = xgb.XGBRegressor()
model.load_model(MODEL_PATH)

FEATURE_NAMES = [
    'Albedo',
    'Building_Density',
    'NDVI',
    'NDWI',
    'total_precipitation_hourly',
    'u_component_of_wind_10m',
    'v_component_of_wind_10m',
    'Longitude',
    'Latitude',
    'Rn_NetRadiation',
    'G_SoilHeatFlux',
    'H_SensibleHeatFlux'
]


class OutputData(BaseModel):
    predicted_lst_celsius: float
    unit: str = "°C"


class PredictionResponse(BaseModel):
    """Pydantic schema for output response structure."""
    status: str = "success"
    inputs: EnvironmentalFeatures
    outputs: OutputData


# ==========================================
# 3. Prediction Function
# ==========================================
def predict_lst_json(input_data: EnvironmentalFeatures) -> str:
    """
    Validates input using Pydantic, passes parameters to XGBoost model,
    and returns a structured JSON string.
    """
    # 1. Parse and validate input through Pydantic model
    if isinstance(input_data, dict):
        validated_input = EnvironmentalFeatures(**input_data)
    else:
        validated_input = input_data

    # 2. Extract validated dict and prepare DataFrame in exact feature order
    input_dict = validated_input.model_dump()
    input_df = pd.DataFrame([input_dict])[FEATURE_NAMES]

    # 3. Model inference
    prediction = float(model.predict(input_df)[0])

    # 4. Construct response using output Pydantic model
    response = PredictionResponse(
        status="success",
        inputs=validated_input,
        outputs=OutputData(predicted_lst_celsius=round(prediction, 2))
    )

    # 5. Return JSON string representation
    return response.model_dump_json(indent=4)


if __name__ == "__main__":
    sample_data = {
        'Albedo': 0.15,
        'Building_Density': 0.65,
        'NDVI': 0.12,
        'NDWI': -0.25,
        'total_precipitation_hourly': 0.0,
        'u_component_of_wind_10m': 1.2,
        'v_component_of_wind_10m': -0.8,
        'Longitude': 77.2090,
        'Latitude': 28.6139,
        'Rn_NetRadiation': 450.0,
        'G_SoilHeatFlux': 85.0,
        'H_SensibleHeatFlux': 180.0
    }

    json_result = predict_lst_json(sample_data)
    print(json_result)