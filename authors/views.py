from django.core.cache import cache
from django.db.models import Avg, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.response import Response

from core.cache_utils import build_list_cache_key, increment_version
from core.exceptions import ConflictError
from core.exceptions import PermissionError as APIPermissionError
from core.permissions import IsAdminOrReadOnly

from .models import Author, AuthorReview
from .serializers import AuthorReviewSerializer, AuthorSerializer

AUTHOR_CACHE_PREFIX = "authors:list"
AUTHOR_REVIEW_CACHE_PREFIX = "author_reviews:list"
CACHE_TIMEOUT = 60 * 15  # 15 minutes


class AuthorViewSet(viewsets.ModelViewSet):
    # Optimization: select_related for the User (OneToOne)
    # Annotation for average and count calculations
    # Prefetch films to avoid N+1
    queryset = (
        Author.objects.select_related("user")
        .prefetch_related("films")
        .annotate(
            average_rating=Avg("reviews__rating"),
            reviews_count=Count("reviews"),
        )
        .all()
    )
    serializer_class = AuthorSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,  # type: ignore[list-item]
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["source"]
    search_fields = ["user__username", "user__email", "bio"]
    ordering_fields = ["date_of_birth", "created_at"]

    def list(self, request, *args, **kwargs):
        """List authors with versioned caching."""
        cache_key = build_list_cache_key(AUTHOR_CACHE_PREFIX, request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=CACHE_TIMEOUT)
        return response

    def _invalidate_author_cache(self):
        """Invalidate the author list cache by incrementing version."""
        increment_version(AUTHOR_CACHE_PREFIX)

    def perform_create(self, serializer):
        """Invalidate cache after creating an author."""
        serializer.save()
        self._invalidate_author_cache()

    def perform_update(self, serializer):
        """Invalidate cache after updating an author."""
        serializer.save()
        self._invalidate_author_cache()

    def perform_destroy(self, instance):
        # Allow deleting an authors only if they have no films (books) associated
        if instance.films.exists():
            raise ConflictError(
                detail="Impossible to delete an author who has associated films.",
                code="AUTHOR_HAS_FILMS",
            )
        instance.delete()
        self._invalidate_author_cache()


class AuthorReviewViewSet(viewsets.ModelViewSet):
    queryset = AuthorReview.objects.select_related("author", "user__user").all()
    serializer_class = AuthorReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        """List author reviews with versioned caching."""
        cache_key = build_list_cache_key(AUTHOR_REVIEW_CACHE_PREFIX, request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=CACHE_TIMEOUT)
        return response

    def _invalidate_author_review_cache(self):
        """Invalidate the author reviews cache by incrementing version."""
        increment_version(AUTHOR_REVIEW_CACHE_PREFIX)

    def perform_create(self, serializer):
        if not hasattr(self.request.user, "spectator_profile"):
            raise APIPermissionError(
                detail="Only spectators can leave a review.",
                code="SPECTATOR_REQUIRED",
            )
        serializer.save(user=self.request.user.spectator_profile)
        self._invalidate_author_review_cache()

    def perform_update(self, serializer):
        serializer.save()
        self._invalidate_author_review_cache()

    def perform_destroy(self, instance):
        instance.delete()
        self._invalidate_author_review_cache()
