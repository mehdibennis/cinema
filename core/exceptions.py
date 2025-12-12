"""
Custom exception handling for consistent API error responses.

All API errors follow this format:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": {...}  # Optional additional details
    }
}
"""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exception Classes
# =============================================================================


class BaseAPIException(APIException):
    """Base exception for all custom API exceptions."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "error"
    default_detail = "An error has occurred."

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        detail_str: str = detail or self.default_detail
        self.detail = detail_str  # type: ignore[assignment]
        self.code = code or self.default_code
        self.extra = extra or {}
        super().__init__(detail=detail_str, code=self.code)


class NotFoundError(BaseAPIException):
    """Resource not found."""

    status_code = status.HTTP_404_NOT_FOUND  # type: ignore[assignment]
    default_code = "NOT_FOUND"
    default_detail = "Resource not found."


class ValidationError(BaseAPIException):
    """Validation error."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "VALIDATION_ERROR"
    default_detail = "Invalid data."


class AuthenticationError(BaseAPIException):
    """Authentication error."""

    status_code = status.HTTP_401_UNAUTHORIZED  # type: ignore[assignment]
    default_code = "AUTHENTICATION_ERROR"
    default_detail = "Authentication required."


class PermissionError(BaseAPIException):
    """Permission denied error."""

    status_code = status.HTTP_403_FORBIDDEN  # type: ignore[assignment]
    default_code = "PERMISSION_DENIED"
    default_detail = "You do not have the necessary permissions."


class ConflictError(BaseAPIException):
    """Conflict error (e.g., duplicate resource)."""

    status_code = status.HTTP_409_CONFLICT  # type: ignore[assignment]
    default_code = "CONFLICT"
    default_detail = "Conflict with an existing resource."


class RateLimitError(BaseAPIException):
    """Rate limit exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS  # type: ignore[assignment]
    default_code = "RATE_LIMIT_EXCEEDED"
    default_detail = "Too many requests. Please try again later."


class ServiceUnavailableError(BaseAPIException):
    """External service unavailable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE  # type: ignore[assignment]
    default_code = "SERVICE_UNAVAILABLE"
    default_detail = "Service temporarily unavailable."


class ExternalAPIError(BaseAPIException):
    """Error from external API (e.g., TMDb)."""

    status_code = status.HTTP_502_BAD_GATEWAY  # type: ignore[assignment]
    default_code = "EXTERNAL_API_ERROR"
    default_detail = "Error communicating with the external service."


# =============================================================================
# Error Response Builder
# =============================================================================


def build_error_response(
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    field_errors: dict[str, list[str]] | None = None,
) -> Response:
    """
    Build a standardized error response.

    Args:
        code: Error code (e.g., "VALIDATION_ERROR")
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        field_errors: Field-specific validation errors

    Returns:
        DRF Response with standardized error format
    """
    error_data: dict[str, Any] = {
        "code": code,
        "message": message,
    }

    if details:
        error_data["details"] = details

    if field_errors:
        error_data["field_errors"] = field_errors

    response_data = {
        "success": False,
        "error": error_data,
    }

    return Response(response_data, status=status_code)


# =============================================================================
# Custom Exception Handler
# =============================================================================


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom exception handler for DRF that provides consistent error responses.

    This handler catches all exceptions and formats them in a standardized way.
    """
    # Log the exception
    request = context.get("request")
    logger.error(
        f"API Exception: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={
            "view": context.get("view").__class__.__name__ if context.get("view") else None,
            "request_path": request.path if request else None,
        },
    )

    # Handle our custom exceptions
    if isinstance(exc, BaseAPIException):
        return build_error_response(
            code=exc.code,
            message=str(exc.detail),
            status_code=exc.status_code,
            details=exc.extra if exc.extra else None,
        )

    # Handle Django's Http404
    if isinstance(exc, Http404):
        return build_error_response(
            code="NOT_FOUND",
            message=str(exc) if str(exc) != "" else "Resource not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Handle Django's PermissionDenied
    if isinstance(exc, PermissionDenied):
        return build_error_response(
            code="PERMISSION_DENIED",
            message=str(exc) if str(exc) else "You do not have the necessary permissions.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Handle Django's ValidationError
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            field_errors = {field: [str(e) for e in errors] for field, errors in exc.message_dict.items()}
            return build_error_response(
                code="VALIDATION_ERROR",
                message="Invalid data.",
                status_code=status.HTTP_400_BAD_REQUEST,
                field_errors=field_errors,
            )
        return build_error_response(
            code="VALIDATION_ERROR",
            message=str(exc.message) if hasattr(exc, "message") else str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Handle Django's IntegrityError (duplicate key, foreign key violations, etc.)
    if isinstance(exc, IntegrityError):
        error_message = str(exc)
        # Parse common integrity errors
        if "duplicate key" in error_message.lower():
            if "user_id" in error_message:
                message = "This user already has an author profile."
            else:
                message = "This resource already exists."
            return build_error_response(
                code="DUPLICATE_RESOURCE",
                message=message,
                status_code=status.HTTP_409_CONFLICT,
            )
        elif "foreign key" in error_message.lower():
            return build_error_response(
                code="INVALID_REFERENCE",
                message="The reference to a related resource is invalid.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        elif "null value" in error_message.lower():
            return build_error_response(
                code="MISSING_REQUIRED_FIELD",
                message="A required field is missing.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        # Generic integrity error
        return build_error_response(
            code="INTEGRITY_ERROR",
            message="The operation violates a database integrity constraint.",
            status_code=status.HTTP_409_CONFLICT,
        )

    # Get standard DRF response first
    response = exception_handler(exc, context)

    if response is not None:
        # Handle DRF's built-in exceptions
        return _handle_drf_exception(exc, response)

    # Unhandled exception - return generic 500 error
    # In production, don't expose internal error details
    return build_error_response(
        code="INTERNAL_ERROR",
        message="An internal error has occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _handle_drf_exception(exc: Exception, response: Response) -> Response:
    """Handle DRF's built-in exceptions and format them consistently."""

    # Determine error code based on status
    status_code = response.status_code
    code = _get_error_code_from_status(status_code, exc)

    # Extract error message
    message, field_errors = _extract_error_details(response.data)

    return build_error_response(
        code=code,
        message=message,
        status_code=status_code,
        field_errors=field_errors if field_errors else None,
    )


def _get_error_code_from_status(status_code: int, exc: Exception) -> str:
    """Get error code based on HTTP status and exception type."""
    if isinstance(exc, NotAuthenticated):
        return "NOT_AUTHENTICATED"
    if isinstance(exc, AuthenticationFailed):
        return "AUTHENTICATION_FAILED"

    status_code_map = {
        400: "VALIDATION_ERROR",
        401: "AUTHENTICATION_ERROR",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        406: "NOT_ACCEPTABLE",
        409: "CONFLICT",
        415: "UNSUPPORTED_MEDIA_TYPE",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }

    return status_code_map.get(status_code, "ERROR")


def _extract_error_details(data: Any) -> tuple[str, dict[str, list[str]] | None]:
    """
    Extract error message and field errors from DRF response data.

    Returns:
        Tuple of (message, field_errors)
    """
    if isinstance(data, str):
        return data, None

    if isinstance(data, list):
        # List of error messages
        return "; ".join(str(item) for item in data), None

    if isinstance(data, dict):
        # Check for 'detail' key (standard DRF error)
        if "detail" in data:
            detail = data["detail"]
            if isinstance(detail, str):
                return detail, None
            if isinstance(detail, list):
                return "; ".join(str(item) for item in detail), None
            if isinstance(detail, dict):
                return str(detail), None

        # Check for 'non_field_errors'
        if "non_field_errors" in data:
            non_field = data["non_field_errors"]
            message = "; ".join(str(item) for item in non_field) if isinstance(non_field, list) else str(non_field)

            # Get remaining field errors
            field_errors = {
                k: [str(e) for e in (v if isinstance(v, list) else [v])]
                for k, v in data.items()
                if k != "non_field_errors"
            }
            return message, field_errors if field_errors else None

        # Field-level validation errors
        field_errors = {}
        messages: list[str] = []
        for key, value in data.items():
            if isinstance(value, list):
                field_errors[key] = [str(v) for v in value]
                messages.extend(str(v) for v in value)
            else:
                field_errors[key] = [str(value)]
                messages.append(str(value))

        message = "Validation errors." if field_errors else "Invalid data."
        return message, field_errors if field_errors else None

    return "An error has occurred.", None


# =============================================================================
# Success Response Builder (for consistency)
# =============================================================================


def build_success_response(
    data: Any = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """
    Build a standardized success response.

    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code (default 200)

    Returns:
        DRF Response with standardized success format
    """
    response_data: dict[str, Any] = {
        "success": True,
    }

    if message:
        response_data["message"] = message

    if data is not None:
        response_data["data"] = data

    return Response(response_data, status=status_code)
