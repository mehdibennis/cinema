from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from authors.factories import AuthorFactory
from authors.models import Author, AuthorReview
from films.factories import FilmFactory
from spectators.factories import SpectatorFactory
from users.factories import AdminUserFactory, AuthorUserFactory, UserFactory


@pytest.mark.django_db
class TestAuthorViewSet:

    def test_list_authors(self, api_client):
        AuthorFactory.create_batch(3)
        url = reverse("author-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_list_authors_filter_source(self, api_client):
        AuthorFactory(tmdb_id=123, source="TMDB")
        AuthorFactory(tmdb_id=None, source="ADMIN")

        url = reverse("author-list")

        # Test tmdb source
        response = api_client.get(url, {"source": "TMDB"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["tmdb_id"] is not None

        # Test local source
        response = api_client.get(url, {"source": "ADMIN"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["tmdb_id"] is None

    def test_create_author_admin(self, api_client):
        """Test creating an author as admin."""
        admin = AdminUserFactory()
        author_user = AuthorUserFactory()
        api_client.force_authenticate(user=admin)

        url = reverse("author-list")
        data = {"user": author_user.id, "bio": "A great author", "source": "ADMIN"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Author.objects.count() == 1
        assert Author.objects.first().bio == "A great author"

    def test_create_author_non_admin_forbidden(self, api_client):
        """Test that non-admin users cannot create authors."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        url = reverse("author-list")
        data = {"bio": "A great author"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_author_admin(self, api_client):
        """Test updating an author as admin."""
        author = AuthorFactory(bio="Old bio")
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)

        url = reverse("author-detail", args=[author.id])
        response = api_client.patch(url, {"bio": "New bio"})
        assert response.status_code == status.HTTP_200_OK
        author.refresh_from_db()
        assert author.bio == "New bio"

    def test_create_author_review(self, api_client):
        author = AuthorFactory()
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)

        url = reverse("authorreview-list")
        data = {"author": author.id, "rating": 5, "comment": "Great author!"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert AuthorReview.objects.count() == 1
        assert AuthorReview.objects.first().user == spectator

    def test_create_author_review_non_spectator_forbidden(self, api_client):
        """Test that non-spectator users cannot create author reviews."""
        author = AuthorFactory()
        user = UserFactory()  # User without spectator profile
        api_client.force_authenticate(user=user)

        url = reverse("authorreview-list")
        data = {"author": author.id, "rating": 5, "comment": "Great author!"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert "SPECTATOR_REQUIRED" in response.data["error"]["code"]

    def test_update_author_review(self, api_client):
        """Test updating an author review."""
        spectator = SpectatorFactory()
        author = AuthorFactory()
        review = AuthorReview.objects.create(author=author, user=spectator, rating=3, comment="Good")
        api_client.force_authenticate(user=spectator.user)

        url = reverse("authorreview-detail", args=[review.id])
        response = api_client.patch(url, {"rating": 5, "comment": "Excellent!"})
        assert response.status_code == status.HTTP_200_OK
        review.refresh_from_db()
        assert review.rating == 5
        assert review.comment == "Excellent!"

    def test_delete_author_review(self, api_client):
        """Test deleting an author review."""
        spectator = SpectatorFactory()
        author = AuthorFactory()
        review = AuthorReview.objects.create(author=author, user=spectator, rating=3, comment="Good")
        api_client.force_authenticate(user=spectator.user)

        url = reverse("authorreview-detail", args=[review.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not AuthorReview.objects.filter(id=review.id).exists()

    def test_delete_author_with_films(self, api_client):
        author = AuthorFactory()
        film = FilmFactory()
        film.authors.add(author)
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)

        url = reverse("author-detail", args=[author.id])
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "AUTHOR_HAS_FILMS"
        assert Author.objects.filter(id=author.id).exists()

    def test_delete_author_without_films(self, api_client):
        author = AuthorFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)

        url = reverse("author-detail", args=[author.id])
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Author.objects.filter(id=author.id).exists()


@pytest.mark.django_db
class TestAuthorCacheInvalidation:
    """Tests for versioned cache invalidation."""

    @patch("authors.views.increment_version")
    def test_create_author_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when creating an author."""
        admin = AdminUserFactory()
        author_user = AuthorUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("author-list")
        response = api_client.post(url, {"user": author_user.id, "bio": "Test", "source": "ADMIN"})
        assert response.status_code == status.HTTP_201_CREATED
        mock_increment.assert_called_once_with("authors:list")

    @patch("authors.views.increment_version")
    def test_update_author_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when updating an author."""
        author = AuthorFactory(bio="Old bio")
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("author-detail", args=[author.id])
        response = api_client.patch(url, {"bio": "New bio"})
        assert response.status_code == status.HTTP_200_OK
        mock_increment.assert_called_once_with("authors:list")

    @patch("authors.views.increment_version")
    def test_delete_author_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when deleting an author."""
        author = AuthorFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("author-detail", args=[author.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_increment.assert_called_once_with("authors:list")

    @patch("authors.views.increment_version")
    def test_create_author_review_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when creating an author review."""
        spectator = SpectatorFactory()
        author = AuthorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("authorreview-list")
        response = api_client.post(url, {"author": author.id, "rating": 5, "comment": "Great!"})
        assert response.status_code == status.HTTP_201_CREATED
        mock_increment.assert_called_once_with("author_reviews:list")
