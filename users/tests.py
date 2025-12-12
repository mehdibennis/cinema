import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from spectators.factories import SpectatorFactory
from users.factories import AdminUserFactory
from users.models import Role

User = get_user_model()


@pytest.mark.django_db
class TestUsersManagers:

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(username="superadmin", email="super@admin.com", password="foo")
        assert admin_user.email == "super@admin.com"
        assert admin_user.is_active is True
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True
        assert admin_user.role == Role.ADMIN
        assert str(admin_user) == "superadmin"


@pytest.mark.django_db
class TestUserViewSet:

    def test_list_users_admin(self, api_client):
        admin = AdminUserFactory()
        SpectatorFactory()
        url = reverse("customuser-list")

        api_client.force_authenticate(user=admin)
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Admin + Spectator = 2 users
        assert len(response.data["results"]) >= 2

    def test_list_users_spectator(self, api_client):
        spectator = SpectatorFactory()
        url = reverse("customuser-list")

        api_client.force_authenticate(user=spectator.user)
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_anonymous(self, api_client):
        url = reverse("customuser-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
