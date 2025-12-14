from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.cache_utils import increment_version
from core.exceptions import (
    NotFoundError,
    build_success_response,
)
from core.exceptions import (
    PermissionError as APIPermissionError,
)
from core.exceptions import (
    ValidationError as APIValidationError,
)
from films.models import Film
from films.serializers import FilmSerializer

from .models import Spectator
from .serializers import SpectatorSerializer, UserRegistrationSerializer

SPECTATOR_CACHE_PREFIX = "spectators:list"


class SpectatorRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        """Invalidate the cache after creating a spectator."""
        serializer.save()
        increment_version(SPECTATOR_CACHE_PREFIX)


class SpectatorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to view spectator profiles.
    ReadOnly because spectators are created via registration.
    """

    queryset = (
        Spectator.objects.select_related("user")
        .prefetch_related("favorite_films__authors", "favorite_films__reviews")
        .all()
    )
    serializer_class = SpectatorSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Retrieve own profile.
        """
        if not hasattr(request.user, "spectator_profile"):
            raise NotFoundError(
                detail="Spectator profile not found.",
                code="SPECTATOR_PROFILE_NOT_FOUND",
            )

        serializer = self.get_serializer(request.user.spectator_profile)
        return build_success_response(data=serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="favorites/add",
        permission_classes=[IsAuthenticated],
    )
    def add_favorite(self, request):
        """
        Add a film to favorites.
        Expects a 'film_id' in the body.
        """
        film_id = request.data.get("film_id")
        if not film_id:
            raise APIValidationError(
                detail="film_id required.",
                code="MISSING_FILM_ID",
            )

        film = get_object_or_404(Film, id=film_id)

        if not hasattr(request.user, "spectator_profile"):
            raise APIPermissionError(
                detail="Action reserved for spectators.",
                code="SPECTATOR_REQUIRED",
            )

        request.user.spectator_profile.favorite_films.add(film)
        return build_success_response(message="Film added to favorites.")

    @action(
        detail=False,
        methods=["post"],
        url_path="favorites/remove",
        permission_classes=[IsAuthenticated],
    )
    def remove_favorite(self, request):
        """
        Remove a film from favorites.
        Expects a 'film_id' in the body.
        """
        film_id = request.data.get("film_id")
        if not film_id:
            raise APIValidationError(
                detail="film_id requis.",
                code="MISSING_FILM_ID",
            )

        film = get_object_or_404(Film, id=film_id)

        if hasattr(request.user, "spectator_profile"):
            request.user.spectator_profile.favorite_films.remove(film)

        return build_success_response(message="Film removed from favorites.")

    @action(
        detail=False,
        methods=["get"],
        url_path="favorites",
        permission_classes=[IsAuthenticated],
    )
    def list_favorites(self, request):
        """
        List own favorite films.
        """
        if not hasattr(request.user, "spectator_profile"):
            raise NotFoundError(
                detail="Spectator profile not found.",
                code="SPECTATOR_PROFILE_NOT_FOUND",
            )
        favorites = request.user.spectator_profile.favorite_films.all()

        page = self.paginate_queryset(favorites)
        if page is not None:
            serializer = FilmSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = FilmSerializer(favorites, many=True)
        return build_success_response(data=serializer.data)
