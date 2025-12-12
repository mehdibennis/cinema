"""Tests pour améliorer la couverture des models"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from authors.factories import AuthorFactory
from authors.models import Author
from films.factories import FilmFactory
from films.models import Film, FilmReview
from spectators.factories import SpectatorFactory
from users.factories import UserFactory


@pytest.mark.django_db
class TestFilmModel:
    """Tests for the Film model"""

    def test_film_str_representation(self):
        """Test the string representation of the film"""
        film = FilmFactory(title="Test Movie")
        assert str(film) == "Test Movie"

    def test_film_ordering(self):
        """Test that films are ordered by descending release date"""
        FilmFactory(title="Old Movie", release_date="2020-01-01")
        FilmFactory(title="New Movie", release_date="2023-01-01")

        films = Film.objects.all()
        assert films[0].title == "New Movie"
        assert films[1].title == "Old Movie"


@pytest.mark.django_db
class TestFilmReviewModel:
    """Tests for the FilmReview model"""

    def test_filmreview_str_representation(self):
        """Test the string representation of the review"""
        film = FilmFactory(title="Great Movie")
        spectator = SpectatorFactory()
        review = FilmReview.objects.create(film=film, user=spectator, rating=5, comment="Excellent!")

        review_str = str(review)
        assert "Great Movie" in review_str
        assert "(5/5)" in review_str

    def test_filmreview_unique_together(self):
        """Test that the same spectator cannot create 2 reviews for the same film"""
        film = FilmFactory()
        spectator = SpectatorFactory()

        # First review
        FilmReview.objects.create(film=film, user=spectator, rating=5, comment="Great!")

        # Second review should fail
        with pytest.raises(IntegrityError):
            FilmReview.objects.create(film=film, user=spectator, rating=3, comment="Changed my mind")


@pytest.mark.django_db
class TestAuthorModel:
    """Tests for the Author model"""

    def test_author_validation_spectator_cannot_be_author(self):
        """Test that a spectator cannot have an Author profile"""
        spectator_user = UserFactory(role="spectator")
        author = Author(user=spectator_user, tmdb_id=999)

        with pytest.raises(ValidationError) as excinfo:
            author.clean()

        assert "spectator" in str(excinfo.value).lower()

    def test_author_save_calls_clean(self):
        """Test that save() calls clean() automatically"""
        spectator_user = UserFactory(role="spectator")
        author = Author(user=spectator_user, tmdb_id=999)

        with pytest.raises(ValidationError):
            author.save()

    def test_author_with_valid_role(self):
        """Test that an Author can be created with an author or admin role"""
        author_user = UserFactory(role="author")
        author = Author(user=author_user, tmdb_id=999)
        author.clean()
        author.save()
        assert author.user.role == "author"

    def test_author_str_representation(self):
        """Test the string representation of the author"""
        user = UserFactory(first_name="John", last_name="Doe", role="author")
        author = AuthorFactory(user=user)

        author_str = str(author)
        assert "John" in author_str and "Doe" in author_str
