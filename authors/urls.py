from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuthorReviewViewSet, AuthorViewSet

router = DefaultRouter()
router.register(r"authors", AuthorViewSet)
router.register(r"author-reviews", AuthorReviewViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
