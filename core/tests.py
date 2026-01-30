"""
Tests for core module views and utilities.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

from core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
    _extract_error_details,
    _get_error_code_from_status,
    _handle_base_api_exception,
    _handle_django_validation_error,
    _handle_drf_builtin_exception,
    _handle_http404,
    _handle_integrity_error,
    _handle_permission_denied,
    _log_exception,
    _parse_integrity_error,
    build_error_response,
    build_success_response,
    custom_exception_handler,
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


class TestCustomExceptionHandler:
    """Tests for custom_exception_handler and helper functions."""

    def test_log_exception(self) -> None:
        """Test _log_exception logs correctly."""
        exc = ValueError("Test error")
        context = {"request": MagicMock(path="/test/"), "view": MagicMock()}
        with patch("core.exceptions.logger") as mock_logger:
            _log_exception(exc, context)
            mock_logger.error.assert_called_once()

    def test_log_exception_no_request(self) -> None:
        """Test _log_exception with no request."""
        exc = ValueError("Test error")
        context = {"request": None, "view": None}
        with patch("core.exceptions.logger") as mock_logger:
            _log_exception(exc, context)
            mock_logger.error.assert_called_once()

    def test_handle_base_api_exception(self) -> None:
        """Test _handle_base_api_exception with custom exception."""
        exc = NotFoundError(detail="Resource not found", extra={"id": 123})
        context: dict[str, Any] = {}
        response = _handle_base_api_exception(exc, context)
        assert response is not None
        assert response.status_code == 404

    def test_handle_base_api_exception_not_applicable(self) -> None:
        """Test _handle_base_api_exception with non-API exception."""
        exc = ValueError("Not an API exception")
        context: dict[str, Any] = {}
        response = _handle_base_api_exception(exc, context)
        assert response is None

    def test_handle_http404(self) -> None:
        """Test _handle_http404."""
        exc = Http404("Page not found")
        context: dict[str, Any] = {}
        response = _handle_http404(exc, context)
        assert response is not None
        assert response.status_code == 404
        assert response.data["error"]["code"] == "NOT_FOUND"

    def test_handle_http404_empty_message(self) -> None:
        """Test _handle_http404 with empty message."""
        exc = Http404("")
        context: dict[str, Any] = {}
        response = _handle_http404(exc, context)
        assert response is not None
        assert response.data["error"]["message"] == "Resource not found."

    def test_handle_http404_not_applicable(self) -> None:
        """Test _handle_http404 with non-404 exception."""
        exc = ValueError("Not a 404")
        context: dict[str, Any] = {}
        response = _handle_http404(exc, context)
        assert response is None

    def test_handle_permission_denied(self) -> None:
        """Test _handle_permission_denied."""
        exc = PermissionDenied("Access denied")
        context: dict[str, Any] = {}
        response = _handle_permission_denied(exc, context)
        assert response is not None
        assert response.status_code == 403

    def test_handle_permission_denied_empty_message(self) -> None:
        """Test _handle_permission_denied with empty message."""
        exc = PermissionDenied()
        context: dict[str, Any] = {}
        response = _handle_permission_denied(exc, context)
        assert response is not None
        assert "permissions" in response.data["error"]["message"].lower()

    def test_handle_permission_denied_not_applicable(self) -> None:
        """Test _handle_permission_denied with non-permission exception."""
        exc = ValueError("Not a permission error")
        context: dict[str, Any] = {}
        response = _handle_permission_denied(exc, context)
        assert response is None

    def test_handle_django_validation_error_with_message_dict(self) -> None:
        """Test _handle_django_validation_error with message_dict."""
        exc = DjangoValidationError({"field1": ["Error 1"], "field2": ["Error 2"]})
        context: dict[str, Any] = {}
        response = _handle_django_validation_error(exc, context)
        assert response is not None
        assert response.status_code == 400
        assert "field_errors" in response.data["error"]

    def test_handle_django_validation_error_simple(self) -> None:
        """Test _handle_django_validation_error with simple message."""
        exc = DjangoValidationError("Simple validation error")
        context: dict[str, Any] = {}
        response = _handle_django_validation_error(exc, context)
        assert response is not None
        assert response.status_code == 400

    def test_handle_django_validation_error_not_applicable(self) -> None:
        """Test _handle_django_validation_error with non-validation exception."""
        exc = ValueError("Not a validation error")
        context: dict[str, Any] = {}
        response = _handle_django_validation_error(exc, context)
        assert response is None

    def test_handle_integrity_error(self) -> None:
        """Test _handle_integrity_error."""
        exc = IntegrityError("duplicate key value")
        context: dict[str, Any] = {}
        response = _handle_integrity_error(exc, context)
        assert response is not None
        assert response.status_code == 409

    def test_handle_integrity_error_not_applicable(self) -> None:
        """Test _handle_integrity_error with non-integrity exception."""
        exc = ValueError("Not an integrity error")
        context: dict[str, Any] = {}
        response = _handle_integrity_error(exc, context)
        assert response is None

    def test_parse_integrity_error_duplicate_key(self) -> None:
        """Test _parse_integrity_error with duplicate key."""
        response = _parse_integrity_error("duplicate key value violates unique constraint")
        assert response.data["error"]["code"] == "DUPLICATE_RESOURCE"

    def test_parse_integrity_error_duplicate_user_id(self) -> None:
        """Test _parse_integrity_error with user_id duplicate."""
        response = _parse_integrity_error("duplicate key value user_id constraint")
        assert "author profile" in response.data["error"]["message"].lower()

    def test_parse_integrity_error_foreign_key(self) -> None:
        """Test _parse_integrity_error with foreign key violation."""
        response = _parse_integrity_error("foreign key constraint failed")
        assert response.data["error"]["code"] == "INVALID_REFERENCE"

    def test_parse_integrity_error_null_value(self) -> None:
        """Test _parse_integrity_error with null value violation."""
        response = _parse_integrity_error("null value in column not allowed")
        assert response.data["error"]["code"] == "MISSING_REQUIRED_FIELD"

    def test_parse_integrity_error_generic(self) -> None:
        """Test _parse_integrity_error with generic error."""
        response = _parse_integrity_error("some other integrity error")
        assert response.data["error"]["code"] == "INTEGRITY_ERROR"

    def test_handle_drf_builtin_exception(self) -> None:
        """Test _handle_drf_builtin_exception."""
        from rest_framework.exceptions import ValidationError as DRFValidationError

        exc = DRFValidationError({"field": ["error"]})
        context = {"request": MagicMock(), "view": MagicMock()}
        response = _handle_drf_builtin_exception(exc, context)
        assert response is not None

    def test_handle_drf_builtin_exception_not_applicable(self) -> None:
        """Test _handle_drf_builtin_exception with non-DRF exception."""
        exc = ValueError("Not a DRF exception")
        context = {"request": MagicMock(), "view": MagicMock()}
        response = _handle_drf_builtin_exception(exc, context)
        assert response is None

    def test_get_error_code_from_status_not_authenticated(self) -> None:
        """Test _get_error_code_from_status with NotAuthenticated."""
        exc = NotAuthenticated()
        code = _get_error_code_from_status(401, exc)
        assert code == "NOT_AUTHENTICATED"

    def test_get_error_code_from_status_authentication_failed(self) -> None:
        """Test _get_error_code_from_status with AuthenticationFailed."""
        exc = AuthenticationFailed()
        code = _get_error_code_from_status(401, exc)
        assert code == "AUTHENTICATION_FAILED"

    def test_get_error_code_from_status_by_code(self) -> None:
        """Test _get_error_code_from_status with various status codes."""
        exc = ValueError()
        assert _get_error_code_from_status(400, exc) == "VALIDATION_ERROR"
        assert _get_error_code_from_status(403, exc) == "PERMISSION_DENIED"
        assert _get_error_code_from_status(404, exc) == "NOT_FOUND"
        assert _get_error_code_from_status(405, exc) == "METHOD_NOT_ALLOWED"
        assert _get_error_code_from_status(429, exc) == "RATE_LIMIT_EXCEEDED"
        assert _get_error_code_from_status(500, exc) == "INTERNAL_ERROR"
        assert _get_error_code_from_status(999, exc) == "ERROR"

    def test_extract_error_details_string(self) -> None:
        """Test _extract_error_details with string input."""
        message, field_errors = _extract_error_details("Simple error")
        assert message == "Simple error"
        assert field_errors is None

    def test_extract_error_details_list(self) -> None:
        """Test _extract_error_details with list input."""
        message, field_errors = _extract_error_details(["Error 1", "Error 2"])
        assert "Error 1" in message
        assert "Error 2" in message
        assert field_errors is None

    def test_extract_error_details_dict_with_detail_string(self) -> None:
        """Test _extract_error_details with dict containing detail string."""
        message, field_errors = _extract_error_details({"detail": "Detailed error"})
        assert message == "Detailed error"

    def test_extract_error_details_dict_with_detail_list(self) -> None:
        """Test _extract_error_details with dict containing detail list."""
        message, field_errors = _extract_error_details({"detail": ["Error 1", "Error 2"]})
        assert "Error 1" in message

    def test_extract_error_details_dict_with_detail_dict(self) -> None:
        """Test _extract_error_details with dict containing detail dict."""
        message, field_errors = _extract_error_details({"detail": {"key": "value"}})
        assert message is not None

    def test_extract_error_details_dict_with_non_field_errors(self) -> None:
        """Test _extract_error_details with non_field_errors."""
        data = {"non_field_errors": ["General error"], "field1": ["Field error"]}
        message, field_errors = _extract_error_details(data)
        assert "General error" in message
        assert field_errors is not None
        assert "field1" in field_errors

    def test_extract_error_details_dict_field_errors(self) -> None:
        """Test _extract_error_details with field-level errors."""
        data = {"field1": ["Error 1"], "field2": "Error 2"}
        message, field_errors = _extract_error_details(data)
        assert field_errors is not None
        assert "field1" in field_errors
        assert "field2" in field_errors

    def test_extract_error_details_unknown_type(self) -> None:
        """Test _extract_error_details with unknown type."""
        message, field_errors = _extract_error_details(12345)
        assert message == "An error has occurred."
        assert field_errors is None

    def test_custom_exception_handler_unhandled(self) -> None:
        """Test custom_exception_handler with unhandled exception."""
        exc = Exception("Unhandled error")
        context = {"request": MagicMock(path="/test/"), "view": MagicMock()}
        with patch("core.exceptions.logger"):
            response = custom_exception_handler(exc, context)
        assert response is not None
        assert response.status_code == 500
        assert response.data["error"]["code"] == "INTERNAL_ERROR"


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
