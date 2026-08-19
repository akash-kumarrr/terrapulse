import inspect
from unittest.mock import patch

from app.services.geodata_extractor import CityDataRequest, extract_city_environmental_data


def test_extract_city_environmental_data_is_async():
    assert inspect.iscoroutinefunction(extract_city_environmental_data)


def test_uses_project_id_from_request_without_local_gcloud_checks():
    with patch("app.services.geodata_extractor.ee.Initialize") as initialize_mock:
        import app.services.geodata_extractor as geodata
        geodata._initialize_earth_engine("custom-project")

    initialize_mock.assert_called_once_with(project="custom-project")
