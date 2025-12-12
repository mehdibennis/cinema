from django.contrib.auth import get_user_model
from rest_framework import serializers

from films.serializers import FilmSerializer

from .models import Spectator

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name")

    def create(self, validated_data):
        # Force the role to SPECTATOR by default during API registration
        validated_data["role"] = "spectator"
        user = User.objects.create_user(**validated_data)
        # Créer le profil spectateur associé
        Spectator.objects.create(user=user)
        return user


class SpectatorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    favorite_films = FilmSerializer(many=True, read_only=True)

    class Meta:
        model = Spectator
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "favorite_genre",
            "bio",
            "avatar",
            "favorite_films",
        ]
