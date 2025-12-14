from rest_framework import serializers

from .models import Film, FilmReview


class FilmReviewSerializer(serializers.ModelSerializer):
    user: serializers.StringRelatedField = serializers.StringRelatedField(read_only=True)  # type: ignore[assignment]
    film_title: serializers.CharField = serializers.CharField(  # type: ignore[assignment]
        source="film.title", read_only=True
    )

    class Meta:
        model = FilmReview
        fields = ["id", "user", "film", "film_title", "rating", "comment", "created_at"]
        read_only_fields = ["user", "created_at", "film_title"]


class AuthorNestedSerializer(serializers.Serializer):
    """Minimal serializer for the author nested in a film (avoids circular reference)."""

    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    date_of_birth = serializers.DateField(read_only=True)
    bio = serializers.CharField(read_only=True)
    tmdb_id = serializers.IntegerField(read_only=True)
    photo = serializers.ImageField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class FilmSerializer(serializers.ModelSerializer):
    authors = AuthorNestedSerializer(many=True, read_only=True)

    # To allow adding authors via ID during creation/modification:
    author_ids = serializers.PrimaryKeyRelatedField(
        write_only=True,
        many=True,
        queryset=Film._meta.get_field("authors").related_model.objects.all(),  # type: ignore[union-attr]
        source="authors",
    )

    reviews = FilmReviewSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(source="avg_rating", read_only=True)

    class Meta:
        model = Film
        fields = [
            "id",
            "title",
            "description",
            "release_date",
            "evaluation",
            "status",
            "authors",
            "author_ids",
            "tmdb_id",
            "poster",
            "reviews",
            "average_rating",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "average_rating"]
