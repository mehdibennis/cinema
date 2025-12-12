from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from films.factories import FilmFactory
from films.models import Film
from spectators.factories import SpectatorFactory
from users.factories import AdminUserFactory


@pytest.mark.django_db
class TestFilmViewSet:

    def test_list_films(self, api_client):
        FilmFactory.create_batch(3)
        url = reverse("film-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_list_films_filter_source(self, api_client):
        FilmFactory(tmdb_id=123, source="TMDB")
        FilmFactory(tmdb_id=None, source="ADMIN")

        url = reverse("film-list")

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

    def test_create_film_review(self, api_client):
        film = FilmFactory()
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)

        url = reverse("filmreview-list")
        data = {"film": film.id, "rating": 5, "comment": "Great movie!"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert film.reviews.count() == 1
        assert film.reviews.first().user == spectator

    def test_create_film_admin(self, api_client):
        from authors.factories import AuthorFactory

        author = AuthorFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-list")
        data = {
            "title": "New Movie",
            "description": "Description",
            "release_date": "2023-01-01",
            "evaluation": "PG",
            "status": "draft",
            "author_id": author.id,
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Film.objects.count() == 1

    def test_create_film_unauthorized(self, api_client):
        # Anonymous
        url = reverse("film-list")
        data = {"title": "New Movie"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Spectator
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_archive_film(self, api_client):
        film = FilmFactory(status="published")
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-archive", args=[film.id])
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        film.refresh_from_db()
        assert film.status == "archived"

    def test_filter_films_by_status(self, api_client):
        FilmFactory(status="published")
        FilmFactory(status="draft")
        url = reverse("film-list")
        response = api_client.get(url, {"status": "published"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["status"] == "published"

    def test_filter_films_by_source(self, api_client):
        FilmFactory(tmdb_id=123, source="TMDB")  # TMDb
        FilmFactory(tmdb_id=None, source="ADMIN")  # Local
        url = reverse("film-list")

        # Test TMDb source
        response = api_client.get(url, {"source": "TMDB"})
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["tmdb_id"] == 123

        # Test Local source
        response = api_client.get(url, {"source": "ADMIN"})
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["tmdb_id"] is None


@pytest.mark.django_db
class TestFilmReviewViewSet:
    def test_create_review(self, api_client):
        film = FilmFactory()
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("filmreview-list")
        data = {"film": film.id, "rating": 5, "comment": "Great!"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert film.reviews.count() == 1
        assert film.reviews.first().user == spectator
        # Check that film_title is present in the response
        assert "film_title" in response.data
        assert response.data["film_title"] == film.title

    def test_create_review_non_spectator(self, api_client):
        """Test that non-spectators cannot create reviews."""
        film = FilmFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("filmreview-list")
        data = {"film": film.id, "rating": 5, "comment": "Great!"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "SPECTATOR_REQUIRED"


@pytest.mark.django_db
class TestFilmCRUDOperations:
    """Tests for film update and delete operations."""

    def test_update_film_admin(self, api_client):
        """Test updating a film as admin."""
        film = FilmFactory(title="Old Title")
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-detail", args=[film.id])
        response = api_client.patch(url, {"title": "New Title"})
        assert response.status_code == status.HTTP_200_OK
        film.refresh_from_db()
        assert film.title == "New Title"

    def test_delete_film_admin(self, api_client):
        """Test deleting a film as admin."""
        film = FilmFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-detail", args=[film.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Film.objects.filter(id=film.id).exists()

    def test_update_film_non_admin_forbidden(self, api_client):
        """Test that non-admins cannot update films."""
        film = FilmFactory()
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("film-detail", args=[film.id])
        response = api_client.patch(url, {"title": "Hacked"})
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestFilmCacheInvalidation:
    """Tests for versioned cache invalidation."""

    @patch("films.views.increment_version")
    def test_create_film_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when creating a film."""
        from authors.factories import AuthorFactory

        author = AuthorFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-list")
        data = {
            "title": "Cache Test",
            "description": "Test",
            "release_date": "2023-01-01",
            "evaluation": "PG",
            "status": "draft",
            "author_id": author.id,
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        mock_increment.assert_called_once_with("films:list")

    @patch("films.views.increment_version")
    def test_update_film_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when updating a film."""
        film = FilmFactory(title="Old Title")
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-detail", args=[film.id])
        response = api_client.patch(url, {"title": "New Title"})
        assert response.status_code == status.HTTP_200_OK
        mock_increment.assert_called_once_with("films:list")

    @patch("films.views.increment_version")
    def test_delete_film_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when deleting a film."""
        film = FilmFactory()
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-detail", args=[film.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_increment.assert_called_once_with("films:list")

    @patch("films.views.increment_version")
    def test_archive_film_invalidates_cache(self, mock_increment, api_client):
        """Test increment_version is called when archiving a film."""
        film = FilmFactory(status="published")
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        url = reverse("film-archive", args=[film.id])
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        mock_increment.assert_called_once_with("films:list")
