from django.core.cache import cache
from django.db.models import Avg
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.cache_utils import build_list_cache_key, increment_version
from core.exceptions import PermissionError as APIPermissionError
from core.permissions import IsAdminOrReadOnly

from .models import Film, FilmReview
from .serializers import FilmReviewSerializer, FilmSerializer

FILM_CACHE_PREFIX = "films:list"
CACHE_TIMEOUT = 60 * 15  # 15 minutes


class FilmViewSet(viewsets.ModelViewSet):
    # Optimization: select_related for FK (author) and prefetch_related for Reverse FK (reviews)
    queryset = (
        Film.objects.select_related("author")
        .prefetch_related("reviews")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-created_at")
    )
    serializer_class = FilmSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,  # type: ignore[list-item]
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "evaluation", "source"]
    search_fields = ["title", "description"]
    ordering_fields = ["release_date", "created_at", "avg_rating"]

    def list(self, request, *args, **kwargs):
        """List films with versioned caching (avoids global cache clear)."""
        cache_key = build_list_cache_key(FILM_CACHE_PREFIX, request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=CACHE_TIMEOUT)
        return response

    def _invalidate_film_cache(self):
        """Invalidate the film list cache by incrementing version."""
        increment_version(FILM_CACHE_PREFIX)

    def perform_create(self, serializer):
        """Invalidate the cache after creating a film."""
        serializer.save()
        self._invalidate_film_cache()

    def perform_update(self, serializer):
        """Invalidate the cache after updating a film."""
        serializer.save()
        self._invalidate_film_cache()

    def perform_destroy(self, instance):
        """Invalidate the cache after deleting a film."""
        instance.delete()
        self._invalidate_film_cache()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def archive(self, request, pk=None):
        """
        Custom endpoint to archive a film.
        """
        film = self.get_object()
        film.status = "archived"
        film.save()
        self._invalidate_film_cache()
        serializer = self.get_serializer(film)
        return Response(serializer.data)


class FilmReviewViewSet(viewsets.ModelViewSet):
    queryset = FilmReview.objects.select_related("film", "user__user").all()
    serializer_class = FilmReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Automatically associate the connected spectator
        if not hasattr(self.request.user, "spectator_profile"):
            raise APIPermissionError(
                detail="Only spectators can rate a film.",
                code="SPECTATOR_REQUIRED",
            )
        serializer.save(user=self.request.user.spectator_profile)
