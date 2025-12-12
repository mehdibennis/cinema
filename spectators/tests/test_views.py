from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from films.factories import FilmFactory
from spectators.factories import SpectatorFactory
from spectators.models import Spectator
from users.models import CustomUser


@pytest.mark.django_db
class TestSpectatorAuth:

    def test_register_spectator(self, api_client):
        url = reverse("register")
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert CustomUser.objects.filter(username="newuser").exists()
        assert Spectator.objects.filter(user__username="newuser").exists()

    @patch("spectators.views.increment_version")
    def test_register_spectator_invalidates_cache(self, mock_increment, api_client):
        """Test that increment_version is called when registering a spectator."""
        url = reverse("register")
        data = {
            "username": "cacheuser",
            "email": "cache@example.com",
            "password": "password123",
            "first_name": "Cache",
            "last_name": "User",
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        mock_increment.assert_called_once_with("spectators:list")


@pytest.mark.django_db
class TestSpectatorFavorites:

    def test_add_favorite(self, api_client):
        spectator = SpectatorFactory()
        film = FilmFactory()
        api_client.force_authenticate(user=spectator.user)

        url = reverse("spectator-add-favorite")
        data = {"film_id": film.id}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert spectator.favorite_films.filter(id=film.id).exists()

    def test_remove_favorite(self, api_client):
        spectator = SpectatorFactory()
        film = FilmFactory()
        spectator.favorite_films.add(film)
        api_client.force_authenticate(user=spectator.user)

        url = reverse("spectator-remove-favorite")
        data = {"film_id": film.id}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert not spectator.favorite_films.filter(id=film.id).exists()

    def test_list_favorites(self, api_client):
        spectator = SpectatorFactory()
        films = FilmFactory.create_batch(2)
        spectator.favorite_films.set(films)
        api_client.force_authenticate(user=spectator.user)

        url = reverse("spectator-list-favorites")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

    def test_add_favorite_missing_id(self, api_client):
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("spectator-add-favorite")
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_favorite_invalid_id(self, api_client):
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("spectator-add-favorite")
        response = api_client.post(url, {"film_id": 99999})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_favorite_missing_id(self, api_client):
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("spectator-remove-favorite")
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_favorite_invalid_id(self, api_client):
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("spectator-remove-favorite")
        response = api_client.post(url, {"film_id": 99999})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_me_endpoint(self, api_client):
        spectator = SpectatorFactory()
        api_client.force_authenticate(user=spectator.user)
        url = reverse("spectator-me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["username"] == spectator.user.username

    def test_me_endpoint_no_spectator_profile(self, api_client):
        """Test me endpoint when user has no spectator profile."""
        from users.factories import UserFactory

        user = UserFactory()
        api_client.force_authenticate(user=user)
        url = reverse("spectator-me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "SPECTATOR_PROFILE_NOT_FOUND"

    def test_add_favorite_no_spectator_profile(self, api_client):
        """Test add favorite when user has no spectator profile."""
        from users.factories import UserFactory

        user = UserFactory()
        film = FilmFactory()
        api_client.force_authenticate(user=user)
        url = reverse("spectator-add-favorite")
        response = api_client.post(url, {"film_id": film.id})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "SPECTATOR_REQUIRED"

    def test_list_favorites_no_spectator_profile(self, api_client):
        """Test list favorites when user has no spectator profile."""
        from users.factories import UserFactory

        user = UserFactory()
        api_client.force_authenticate(user=user)
        url = reverse("spectator-list-favorites")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "SPECTATOR_PROFILE_NOT_FOUND"

    def test_list_favorites_no_pagination(self, api_client, settings):
        """Test list favorites when pagination returns None (less items than page size)."""
        spectator = SpectatorFactory()
        film = FilmFactory()
        spectator.favorite_films.add(film)
        api_client.force_authenticate(user=spectator.user)

        with patch("spectators.views.SpectatorViewSet.paginate_queryset", return_value=None):
            url = reverse("spectator-list-favorites")
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data["success"] is True
            assert isinstance(response.data["data"], list)
            assert len(response.data["data"]) == 1
