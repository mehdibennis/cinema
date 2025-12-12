from rest_framework import serializers

from films.models import Film
from users.models import CustomUser

from .models import Author, AuthorReview


class UserNestedSerializer(serializers.ModelSerializer):
    """Nested serializer to display user information."""

    class Meta:
        model = CustomUser
        fields = ["id", "username", "first_name", "last_name", "email"]


class FilmNestedSerializer(serializers.ModelSerializer):
    """Minimal nested serializer to display an author's films."""

    class Meta:
        model = Film
        fields = ["id", "title", "release_date", "status", "tmdb_id"]


class AuthorSerializer(serializers.ModelSerializer):
    # These fields are calculated via annotate() in the queryset
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    # Flattened user fields for a cleaner structure (read-only)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    # Modifiable User fields (not linked to source to avoid conflicts)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    # User field for writing (creation only)
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), write_only=True, required=False)
    # Films by this author
    films = FilmNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Author
        fields = [
            "id",
            "user_id",
            "username",
            "first_name",
            "last_name",
            "email",
            "date_of_birth",
            "bio",
            "tmdb_id",
            "photo",
            "films",
            "average_rating",
            "reviews_count",
            "created_at",
            "updated_at",
            "user",  # Write-only pour création
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "average_rating",
            "reviews_count",
            "user_id",
            "username",
        ]

    def to_representation(self, instance):
        """Customize output to show user fields."""
        data = super().to_representation(instance)
        # Override with actual user data
        data["first_name"] = instance.user.first_name
        data["last_name"] = instance.user.last_name
        data["email"] = instance.user.email
        return data

    def update(self, instance, validated_data):
        """Override update to handle user fields."""
        # Remove user from validated_data (it's the PK reference for create)
        validated_data.pop("user", None)

        # Extract user fields
        user_fields = {}
        for field in ["first_name", "last_name", "email"]:
            if field in validated_data:
                user_fields[field] = validated_data.pop(field)

        # Update user fields if provided
        if user_fields:
            for key, value in user_fields.items():
                setattr(instance.user, key, value)
            instance.user.save()

        # Update author fields
        return super().update(instance, validated_data)


class AuthorReviewSerializer(serializers.ModelSerializer):
    user: serializers.StringRelatedField = serializers.StringRelatedField(read_only=True)  # type: ignore[assignment]
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = AuthorReview
        fields = ["id", "author", "author_name", "user", "rating", "comment", "created_at"]
        read_only_fields = ["user", "created_at", "author_name"]
