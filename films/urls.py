from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FilmReviewViewSet, FilmViewSet

router = DefaultRouter()
router.register(r"films", FilmViewSet)
router.register(r"reviews", FilmReviewViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
