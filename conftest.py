import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def disable_throttling(settings):
    rest_framework_settings = settings.REST_FRAMEWORK.copy()
    rest_framework_settings["DEFAULT_THROTTLE_CLASSES"] = []
    rest_framework_settings["DEFAULT_THROTTLE_RATES"] = {
        "user": None,
        "anon": None,
    }
    settings.REST_FRAMEWORK = rest_framework_settings


@pytest.fixture
def api_client():
    return APIClient()
