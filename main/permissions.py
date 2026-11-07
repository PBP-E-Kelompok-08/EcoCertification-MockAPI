import secrets

from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission, SAFE_METHODS


class InvalidMockAPIKey(APIException):
    status_code = 401
    default_code = "UNAUTHORIZED"
    default_detail = {
        "success": False,
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Kunci API tidak valid",
        },
    }


class HasMockAPIWriteKey(BasePermission):
    """Allow public reads while protecting writes with the shared API key."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        expected = settings.MOCK_API_WRITE_TOKEN
        supplied = request.headers.get("X-Mock-Api-Key", "")
        if expected and supplied and secrets.compare_digest(supplied, expected):
            return True

        raise InvalidMockAPIKey()
