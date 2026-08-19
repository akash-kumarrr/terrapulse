import inspect

from app.services.geodata_extractor import extract_city_environmental_data


def test_extract_city_environmental_data_is_async():
    assert inspect.iscoroutinefunction(extract_city_environmental_data)
