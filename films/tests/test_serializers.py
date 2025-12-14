"""Tests pour améliorer la couverture des serializers"""

import pytest

from authors.serializers import AuthorSerializer
from films.factories import FilmFactory
from films.serializers import FilmReviewSerializer, FilmSerializer
from spectators.factories import SpectatorFactory
from users.factories import AuthorUserFactory


@pytest.mark.django_db
class TestFilmReviewSerializerExtended:
    """Extended tests for FilmReviewSerializer"""

    def test_film_title_source_field(self):
        """Test that film_title uses source='film.title'"""
        film = FilmFactory(title="Amazing Movie")
        spectator = SpectatorFactory()

        from films.models import FilmReview

        review = FilmReview.objects.create(film=film, user=spectator, rating=5, comment="Great!")

        serializer = FilmReviewSerializer(review)
        data = serializer.data

        assert "film_title" in data
        assert data["film_title"] == "Amazing Movie"
        assert "film" in data  # The film ID should also be present


@pytest.mark.django_db
class TestFilmSerializerExtended:
    """Extended tests for FilmSerializer"""

    def test_film_serializer_with_reviews(self):
        """Test that the serializer includes the reviews"""
        film = FilmFactory(title="Movie with Reviews")
        spectator1 = SpectatorFactory()
        spectator2 = SpectatorFactory()

        from films.models import FilmReview

        FilmReview.objects.create(film=film, user=spectator1, rating=5, comment="Great!")
        FilmReview.objects.create(film=film, user=spectator2, rating=4, comment="Good")

        serializer = FilmSerializer(film)
        data = serializer.data

        assert "reviews" in data
        assert len(data["reviews"]) == 2

    def test_film_serializer_author_nested(self):
        """Test that the author is included with their details"""
        user = AuthorUserFactory(first_name="Steven", last_name="Spielberg", email="steven@example.com")
        from authors.models import Author

        author = Author.objects.create(user=user, tmdb_id=123)

        film = FilmFactory(title="E.T.", authors=[author])

        serializer = FilmSerializer(film)
        data = serializer.data

        assert "authors" in data
        assert len(data["authors"]) == 1
        assert data["authors"][0]["username"] == user.username
        assert data["authors"][0]["first_name"] == "Steven"
        assert data["authors"][0]["last_name"] == "Spielberg"


@pytest.mark.django_db
class TestAuthorSerializerExtended:
    """Extended tests for AuthorSerializer"""

    def test_author_serializer_read_only(self):
        """Test that the Author serializer returns data correctly"""
        user = AuthorUserFactory(first_name="Test", last_name="Author")
        from authors.models import Author

        author = Author.objects.create(user=user, date_of_birth="1980-01-01", bio="Test bio")

        serializer = AuthorSerializer(author)
        data = serializer.data

        assert data["username"] == user.username
        assert data["first_name"] == "Test"
        assert data["last_name"] == "Author"

    def test_author_serializer_with_null_bio(self):
        """Test serializer with empty bio"""
        user = AuthorUserFactory(first_name="Test", last_name="Author")
        from authors.models import Author

        author = Author.objects.create(user=user, date_of_birth="1980-01-01", bio="")  # Empty bio
        serializer = AuthorSerializer(author)
        data = serializer.data

        assert "bio" in data
        assert data["bio"] == ""
