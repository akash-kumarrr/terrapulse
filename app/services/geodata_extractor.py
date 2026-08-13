import os
from typing import Optional
import ee
import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
from pydantic import BaseModel, Field

# Load environment variables if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class CityDataRequest(BaseModel):
    city: str = Field(..., description="Name of the city, e.g., 'Austin'")
    state: str = Field(..., description="Name of the state, e.g., 'Texas'")
    gcp_project_id: Optional[str] = Field(None, description="Google Cloud Project ID for Earth Engine")
    start_date: str = Field("2023-06-01", description="Start date for image collection (YYYY-MM-DD)")
    end_date: str = Field("2023-08-31", description="End date for image collection (YYYY-MM-DD)")
    scale: int = Field(100, description="Spatial resolution in meters per pixel sample")
    num_pixels: int = Field(2000, description="Maximum number of rows/pixels to extract")


def extract_city_environmental_data(request: CityDataRequest) -> str:
    """
    Extracts Albedo, Building Density, NDWI, NDVI, Atmospheric parameters, and LST 
    for a given city/state, computes Rn, G, and H physics vectors, and returns 
    the result directly as a JSON string (records orientation).
    """
    project_id = request.gcp_project_id or os.getenv("EARTH_ENGINE_PROJECT")
    if not project_id:
        raise ValueError(
            "[-] Error: Google Cloud Project ID not found. "
            "Provide it in the prompt or set EARTH_ENGINE_PROJECT in your .env file."
        )

    print(f"[1] Initializing Earth Engine with project '{project_id}'...")
    try:
        ee.Initialize(project=project_id)
    except Exception as init_err:
        print(f"[!] Initial connection notice: {init_err}. Executing auth sequence...")
        if hasattr(ee, "Authenticate"):
            ee.Authenticate()
        elif hasattr(ee, "authenticate"):
            ee.authenticate()
        else:
            raise RuntimeError("[-] Earth Engine authentication method not found in package.")
        
        ee.Initialize(project=project_id)

    print(f"[2] Resolving geographic coordinates via Geopy for: {request.city}, {request.state}...")
    geolocator = Nominatim(user_agent="terrapulse-geodata-extractor")
    location = geolocator.geocode(f"{request.city}, {request.state}")
    
    if not location:
        raise ValueError(f"[-] Error: Could not locate boundaries for '{request.city}, {request.state}'. Please verify spelling.")
    
    print(f"[+] Location successfully resolved: {location.address}")

    bbox = location.raw['boundingbox']
    south, north, west, east = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    aoi_geometry = ee.Geometry.Rectangle([west, south, east, north])

    print(f"[3] Fetching Landsat 8 Imagery from {request.start_date} to {request.end_date}...")
    landsat_collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                          .filterBounds(aoi_geometry)
                          .filterDate(request.start_date, request.end_date)
                          .filter(ee.Filter.lt("CLOUD_COVER", 15)))

    count = landsat_collection.size().getInfo()
    print(f"[+] Total cloud-free satellite scenes found: {count}")
    if count == 0:
        raise ValueError("[-] Error: No cloud-free imagery found for specified date range. Try broadening dates.")

    landsat = landsat_collection.median().clip(aoi_geometry)

    print("[4] Calculating environmental indices (NDVI, NDWI, Albedo, LST)...")
    b1 = landsat.select("SR_B1").multiply(0.0000275).add(-0.2)
    b3 = landsat.select("SR_B3").multiply(0.0000275).add(-0.2)
    b4 = landsat.select("SR_B4").multiply(0.0000275).add(-0.2)
    b5 = landsat.select("SR_B5").multiply(0.0000275).add(-0.2)
    b7 = landsat.select("SR_B7").multiply(0.0000275).add(-0.2)

    ndvi = b5.subtract(b4).divide(b5.add(b4)).rename("NDVI")
    ndwi = b3.subtract(b5).divide(b3.add(b5)).rename("NDWI")

    albedo = (b1.multiply(0.356)
              .add(b3.multiply(0.130))
              .add(b4.multiply(0.373))
              .add(b5.multiply(0.085))
              .add(b7.multiply(0.072))
              .subtract(0.0018)).rename("Albedo")

    lst_kelvin = landsat.select("ST_B10").multiply(0.00341802).add(149.0)
    lst_celsius = lst_kelvin.subtract(273.15).rename("LST_Celsius")

    print("[5] Ingesting GHSL Building Density and ERA5 Weather data...")
    building_density = (ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S")
                        .filterBounds(aoi_geometry)
                        .mosaic()
                        .clip(aoi_geometry)
                        .select("built_surface")
                        .rename("Building_Density"))

    era5 = (ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_BY_HOUR")
            .filterBounds(aoi_geometry)
            .filterDate(request.start_date, request.end_date)
            .select(["u_component_of_wind_10m", "v_component_of_wind_10m", "total_precipitation_hourly"])
            .median()
            .clip(aoi_geometry))

    combined_image = ee.Image.cat([albedo, building_density, ndwi, ndvi, lst_celsius, era5])

    print(f"[6] Sampling matrix down to target feature size of {request.num_pixels} pixels...")
    sample_points = combined_image.sample(
        region=aoi_geometry,
        scale=request.scale,  
        numPixels=request.num_pixels,   
        geometries=True   
    )

    print("[7] Downloading raw pixel features from Earth Engine server...")
    features = sample_points.getInfo().get('features', [])
    
    if not features:
        raise ValueError("[-] Error: Boundary matrix contains zero sampleable data points.")

    data_list = []
    for f in features:
        properties = f.get('properties', {})
        if 'geometry' in f and f['geometry'] is not None:
            coords = f['geometry'].get('coordinates', [None, None])
            properties['Longitude'] = coords[0]
            properties['Latitude'] = coords[1]
        data_list.append(properties)

    df = pd.DataFrame(data_list)

    print("[8] Calculating Energy Balance Physics Matrices (Rn, G, H)...")
    SIGMA = 5.67e-8  
    G_SOLAR = 800.0  

    df['NDVI'] = df.get('NDVI', 0.0).fillna(0.0)
    df['Albedo'] = df.get('Albedo', 0.2).fillna(0.2)
    df['LST_Celsius'] = df.get('LST_Celsius', 25.0).fillna(25.0)
    df['u_component_of_wind_10m'] = df.get('u_component_of_wind_10m', 0.0).fillna(0.0)
    df['v_component_of_wind_10m'] = df.get('v_component_of_wind_10m', 0.0).fillna(0.0)

    lst_k = df['LST_Celsius'] + 273.15
    wind_speed = np.sqrt(df['u_component_of_wind_10m']**2 + df['v_component_of_wind_10m']**2)
    emissivity = np.where(df['NDVI'] > 0, 0.95 + 0.04 * df['NDVI'], 0.985)

    df['Rn_NetRadiation'] = (1.0 - df['Albedo']) * G_SOLAR - (emissivity * SIGMA * (lst_k ** 4))
    ndvi_clipped = np.clip(df['NDVI'], 0.01, 0.99)
    df['G_SoilHeatFlux'] = df['Rn_NetRadiation'] * (df['LST_Celsius'] / df['Albedo']) * \
                           (0.0038 * df['Albedo'] + 0.0074 * (df['Albedo']**2)) * \
                           (1.0 - 0.98 * (ndvi_clipped**4))
    
    df['G_SoilHeatFlux'] = df['G_SoilHeatFlux'].fillna(df['Rn_NetRadiation'] * 0.1)
    df['H_SensibleHeatFlux'] = (df['Rn_NetRadiation'] - df['G_SoilHeatFlux']) * \
                               (1.0 - df['NDVI']) * (1.0 + 0.1 * wind_speed)

    # Convert DataFrame directly to JSON string (records orientation)
    json_data = df.to_json(orient="records", date_format="iso")
    return json_data

"""
if __name__ == "__main__":
    print("=== Earth Engine Environmental Extractor Pipeline ===")
    input_city = input("Enter City Name (e.g., Austin): ").strip()
    input_state = input("Enter State/Region Name (e.g., Texas): ").strip()
    input_project = input("Enter GCP Project ID (Leave blank to use environment default): ").strip()
    gcp_id = input_project if input_project else None

    try:
        request_payload = CityDataRequest(
            city=input_city,
            state=input_state,
            gcp_project_id=gcp_id
        )

        json_payload = extract_city_environmental_data(request_payload)
        print("\n==================================================")
        print("[SUCCESS] Pipeline executed perfectly!")
        print(f"[PAYLOAD LENGTH] {len(json_payload)} characters")
        print(f"[SAMPLE OUTPUT] {json_payload}...")
        print("==================================================")
    except Exception as error:
        print(f"\n[PIPELINE EXCEPTION] Execution halted: {error}")
        
        
"""