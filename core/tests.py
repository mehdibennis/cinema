"""
Tests for core module views and utilities.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

from core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
    build_error_response,
    build_success_response,
)


class TestExceptionHandler:
    """Tests for custom exception handling."""

    def test_build_error_response(self) -> None:
        """Test building a standardized error response."""
        response = build_error_response(
            code="TEST_ERROR",
            message="Test error message",
            status_code=400,
            details={"extra": "info"},
        )
        assert response.status_code == 400
        data = response.data
        assert data["success"] is False
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test error message"
        assert data["error"]["details"]["extra"] == "info"

    def test_build_error_response_with_field_errors(self) -> None:
        """Test building error response with field validation errors."""
        response = build_error_response(
            code="VALIDATION_ERROR",
            message="Validation failed",
            status_code=400,
            field_errors={"email": ["Invalid email format"]},
        )
        data = response.data
        assert data["error"]["field_errors"]["email"] == ["Invalid email format"]

    def test_build_success_response(self) -> None:
        """Test building a standardized success response."""
        response = build_success_response(
            data={"id": 1, "name": "Test"},
            message="Operation successful",
        )
        assert response.status_code == 200
        data = response.data
        assert data["success"] is True
        assert data["message"] == "Operation successful"
        assert data["data"]["id"] == 1

    def test_not_found_error(self) -> None:
        """Test NotFoundError exception."""
        exc = NotFoundError(detail="Resource not found", code="RESOURCE_NOT_FOUND")
        assert exc.status_code == 404
        assert exc.code == "RESOURCE_NOT_FOUND"

    def test_validation_error(self) -> None:
        """Test ValidationError exception."""
        exc = ValidationError(detail="Invalid data")
        assert exc.status_code == 400
        assert exc.code == "VALIDATION_ERROR"

    def test_conflict_error(self) -> None:
        """Test ConflictError exception."""
        exc = ConflictError(detail="Resource already exists", extra={"field": "email"})
        assert exc.status_code == 409
        assert exc.extra["field"] == "email"


@pytest.mark.django_db
class TestHealthCheckView:
    """Tests for HealthCheckView."""

    def test_health_check_returns_healthy(self, api_client) -> None:
        """Test health check returns healthy status with all services up."""
        response = api_client.get("/health/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "up"
        assert data["checks"]["cache"]["status"] == "up"

    @patch("core.views.connection")
    def test_health_check_database_failure(self, mock_connection: MagicMock, api_client) -> None:
        """Test health check returns unhealthy when database is down."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database connection failed")
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        response = api_client.get("/health/")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "down"
        assert "error" in data["checks"]["database"]

    @patch("django.core.cache.cache")
    def test_health_check_cache_failure(self, mock_cache: MagicMock, api_client) -> None:
        """Test health check returns unhealthy when cache is down."""
        mock_cache.set.side_effect = Exception("Cache connection failed")

        response = api_client.get("/health/")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["cache"]["status"] == "down"

    @patch("django.core.cache.cache")
    def test_health_check_cache_get_failure(self, mock_cache: MagicMock, api_client) -> None:
        """Test health check when cache get returns wrong value."""
        mock_cache.set.return_value = True
        mock_cache.get.return_value = "wrong_value"

        response = api_client.get("/health/")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["cache"]["status"] == "down"


@pytest.mark.django_db
class TestReadinessCheckView:
    """Tests for ReadinessCheckView."""

    def test_readiness_check_returns_ready(self, api_client) -> None:
        """Test readiness check returns ready status."""
        response = api_client.get("/ready/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"


@pytest.mark.django_db
class TestLivenessCheckView:
    """Tests for LivenessCheckView."""

    def test_liveness_check_returns_alive(self, api_client) -> None:
        """Test liveness check returns alive status."""
        response = api_client.get("/live/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "alive"
