from typing import Optional
from pydantic import BaseModel, Field



class EnvironmentalFeatures(BaseModel):
    """Pydantic schema for validating input features."""
    Albedo: Optional[float] = Field(default=None, description="Surface albedo ratio (0 to 1)")
    Building_Density: Optional[float] = Field(default=None, description="Built-up density index")
    NDVI: Optional[float] = Field(default=None, description="Normalized Difference Vegetation Index")
    NDWI: Optional[float] = Field(default=None, description="Normalized Difference Water Index")
    total_precipitation_hourly: Optional[float] = Field(default=None, description="Hourly rainfall in mm")
    u_component_of_wind_10m: Optional[float] = Field(default=None, description="Eastward wind vector (m/s)")
    v_component_of_wind_10m: Optional[float] = Field(default=None, description="Northward wind vector (m/s)")
    Longitude: Optional[float] = Field(default=None, description="Geographic Longitude")
    Latitude: Optional[float] = Field(default=None, description="Geographic Latitude")
    Rn_NetRadiation: Optional[float] = Field(default=None, description="Net radiation flux")
    G_SoilHeatFlux: Optional[float] = Field(default=None, description="Soil heat flux")
    H_SensibleHeatFlux: Optional[float] = Field(default=None, description="Sensible heat flux")


class OutputData(BaseModel):
    predicted_lst_celsius: float
    unit: str = "°C"


class PredictionResponse(BaseModel):
    status: str = "success"
    inputs: EnvironmentalFeatures
    outputs: OutputData