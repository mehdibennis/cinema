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


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Global fixture to enable database access for all tests.
    This avoids having to add @pytest.mark.django_db to every test class
    and ensures Factory Boy factories work correctly everywhere.
    """
    pass
