"""Tests for TMDB service integration."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from authors.models import Author
from films.models import Film
from films.services import TMDBService
from users.models import CustomUser


@pytest.mark.django_db
class TestTMDBServicePopularMovies:
    """Tests for get_popular_movies method."""

    @patch("films.services.requests.get")
    def test_get_popular_movies_success(self, mock_get):
        """Test successful retrieval of popular movies."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"id": 1, "title": "Test Movie"}]}
        mock_get.return_value = mock_response

        service = TMDBService()
        service.api_key = "fake_key"
        movies = service.get_popular_movies(limit=1)

        assert len(movies) == 1
        assert movies[0]["title"] == "Test Movie"

    @patch("films.services.requests.get")
    def test_get_popular_movies_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = requests.RequestException("API Error")
        service = TMDBService()
        service.api_key = "fake_key"
        movies = service.get_popular_movies()
        assert movies == []

    def test_get_popular_movies_no_api_key(self):
        """Test that empty list is returned when no API key is set."""
        service = TMDBService()
        service.api_key = ""
        movies = service.get_popular_movies()
        assert movies == []


@pytest.mark.django_db
class TestTMDBServiceImportMovie:
    """Tests for import_movie method."""

    @patch("films.services.requests.get")
    def test_import_movie_full_flow(self, mock_get):
        """Test complete movie import flow with director."""
        mock_poster_resp = MagicMock()
        mock_poster_resp.status_code = 200
        mock_poster_resp.content = b"fake_image_data"

        mock_credits_resp = MagicMock()
        mock_credits_resp.status_code = 200
        mock_credits_resp.json.return_value = {
            "crew": [{"job": "Director", "id": 999, "name": "Director Name", "profile_path": "/path.jpg"}]
        }

        mock_person_resp = MagicMock()
        mock_person_resp.status_code = 200
        mock_person_resp.json.return_value = {
            "id": 999,
            "name": "Director Name",
            "birthday": "1970-01-15",
            "biography": "Famous director",
            "profile_path": "/path.jpg",
        }

        def side_effect(url, **kwargs):
            if "credits" in url:
                return mock_credits_resp
            if "/person/999" in url:
                return mock_person_resp
            if "image.tmdb.org" in url:
                return mock_poster_resp
            return MagicMock(status_code=404)

        mock_get.side_effect = side_effect

        service = TMDBService()
        service.api_key = "fake_key"

        movie_data = {
            "id": 100,
            "title": "Imported Movie",
            "overview": "Overview",
            "release_date": "2023-01-01",
            "poster_path": "/poster.jpg",
        }

        film = service.import_movie(movie_data)

        assert film is not None
        assert film.title == "Imported Movie"
        assert film.tmdb_id == 100
        assert film.authors.count() == 1
        author = film.authors.first()
        assert author.tmdb_id == 999
        assert author.user.first_name == "Director"
        assert author.user.last_name == "Name"

    def test_import_movie_missing_data(self):
        """Test import with missing required data."""
        service = TMDBService()
        movie_data = {"id": 1}  # Missing title and release_date
        film = service.import_movie(movie_data)
        assert film is None

    def test_import_movie_missing_tmdb_id(self):
        """Test import_movie when tmdb_id is None."""
        service = TMDBService()
        service.api_key = "fake_key"

        movie_data = {
            "id": None,
            "title": "Movie Without ID",
            "overview": "Test",
            "release_date": "2023-01-01",
        }

        film = service.import_movie(movie_data)
        assert film is None

    @patch("films.services.requests.get")
    def test_import_movie_without_author(self, mock_get):
        """Test import when director fetch fails."""
        mock_get.side_effect = requests.RequestException("API Error")

        service = TMDBService()
        service.api_key = "fake_key"

        movie_data = {
            "id": 200,
            "title": "Movie Without Director",
            "overview": "Test",
            "release_date": "2023-01-01",
            "poster_path": "/poster.jpg",
        }

        film = service.import_movie(movie_data)
        assert film is None

    @patch("films.services.requests.get")
    def test_import_movie_with_poster_download_failure(self, mock_get):
        """Test when poster download fails but movie still created."""
        mock_credits = MagicMock()
        mock_credits.status_code = 200
        mock_credits.json.return_value = {"crew": [{"job": "Director", "id": 888, "name": "Test Director"}]}

        mock_person = MagicMock()
        mock_person.status_code = 200
        mock_person.json.return_value = {"id": 888, "name": "Test Director", "birthday": None, "biography": None}

        mock_poster = MagicMock()
        mock_poster.status_code = 404

        def side_effect(url, **kwargs):
            if "credits" in url:
                return mock_credits
            if "/person/888" in url:
                return mock_person
            if "image.tmdb.org" in url:
                return mock_poster
            return MagicMock(status_code=404)

        mock_get.side_effect = side_effect

        service = TMDBService()
        service.api_key = "fake_key"

        movie_data = {
            "id": 300,
            "title": "Movie With Bad Poster",
            "overview": "Test",
            "release_date": "2023-01-01",
            "poster_path": "/bad_poster.jpg",
        }

        film = service.import_movie(movie_data)
        assert film is not None
        assert film.title == "Movie With Bad Poster"


@pytest.mark.django_db
class TestTMDBServiceDirector:
    """Tests for director fetch and import methods."""

    @patch("films.services.requests.get")
    def test_fetch_and_import_director_api_error(self, mock_get):
        """Test that API error during director fetch returns None."""
        mock_get.side_effect = requests.RequestException("API Error")

        service = TMDBService()
        service.api_key = "fake_key"

        director = service._fetch_and_import_director(123)
        assert director is None

    @patch("films.services.requests.get")
    def test_fetch_and_import_director_no_directors(self, mock_get):
        """Test when no director found in credits."""
        mock_credits = MagicMock()
        mock_credits.status_code = 200
        mock_credits.json.return_value = {
            "crew": [
                {"job": "Producer", "id": 111, "name": "Producer Name"},
                {"job": "Writer", "id": 222, "name": "Writer Name"},
            ]
        }
        mock_get.return_value = mock_credits

        service = TMDBService()
        service.api_key = "fake_key"

        director = service._fetch_and_import_director(999)
        assert director is None

    @patch("films.services.requests.get")
    def test_fetch_person_details_failure(self, mock_get):
        """Test _fetch_person_details with API error."""
        mock_get.side_effect = requests.RequestException("API Error")

        service = TMDBService()
        service.api_key = "fake_key"

        result = service._fetch_person_details(999)
        assert result is None

    @patch("films.services.requests.get")
    def test_fetch_person_details_404(self, mock_get):
        """Test _fetch_person_details with 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        service = TMDBService()
        service.api_key = "fake_key"

        result = service._fetch_person_details(999)
        assert result == {} or result is None


@pytest.mark.django_db
class TestTMDBServiceAuthorImport:
    """Tests for author import functionality."""

    @patch("films.services.requests.get")
    def test_import_author_with_biography(self, mock_get):
        """Test author import with full biography (truncation)."""
        mock_person = MagicMock()
        mock_person.status_code = 200
        mock_person.json.return_value = {"birthday": "1980-05-20", "biography": "A" * 2000}

        mock_photo = MagicMock()
        mock_photo.status_code = 200
        mock_photo.content = b"photo_data"

        def side_effect(url, **kwargs):
            if "/person/" in url and "image.tmdb.org" not in url:
                return mock_person
            if "image.tmdb.org" in url:
                return mock_photo
            return MagicMock(status_code=404)

        mock_get.side_effect = side_effect

        service = TMDBService()
        service.api_key = "fake_key"

        person_data = {"id": 777, "name": "Test Author Name", "profile_path": "/profile.jpg"}

        author = service._import_author(person_data)
        assert author is not None
        assert len(author.bio) <= 1000

    @patch("films.services.requests.get")
    def test_import_author_with_single_name(self, mock_get):
        """Test author import with single name (no last name)."""
        mock_person = MagicMock()
        mock_person.status_code = 200
        mock_person.json.return_value = {"birthday": None, "biography": ""}

        mock_get.return_value = mock_person

        service = TMDBService()
        service.api_key = "fake_key"

        person_data = {"id": 666, "name": "Madonna"}

        author = service._import_author(person_data)
        assert author is not None
        assert author.user.first_name == "Madonna"
        assert author.user.last_name == ""

    def test_import_author_missing_tmdb_id(self):
        """Test author import without tmdb_id."""
        service = TMDBService()
        person_data = {"name": "Test"}

        author = service._import_author(person_data)
        assert author is None

    def test_import_author_missing_name(self):
        """Test author import without name."""
        service = TMDBService()
        person_data = {"id": 123}

        author = service._import_author(person_data)
        assert author is None

    @patch("films.services.requests.get")
    def test_import_author_with_invalid_birthday(self, mock_get):
        """Test author import with invalid birthday format."""
        mock_person = MagicMock()
        mock_person.status_code = 200
        mock_person.json.return_value = {"birthday": "invalid-date", "biography": "Test bio"}

        mock_get.return_value = mock_person

        service = TMDBService()
        service.api_key = "fake_key"

        person_data = {"id": 555, "name": "Test Person"}

        author = service._import_author(person_data)
        assert author is not None
        assert author.date_of_birth is None


@pytest.mark.django_db
class TestTMDBServiceImageDownload:
    """Tests for image download functionality."""

    @patch("films.services.requests.get")
    def test_download_poster_exception_handling(self, mock_get):
        """Test poster download with exception."""
        mock_get.side_effect = Exception("Network error")

        service = TMDBService()
        film = Film(title="Test Film", tmdb_id=123)

        service._download_and_save_poster(film, "/poster.jpg", 123)
        assert not film.poster or film.poster.name in ["", None]

    @patch("films.services.requests.get")
    def test_download_author_photo_exception_handling(self, mock_get):
        """Test author photo download with exception."""
        mock_get.side_effect = Exception("Network error")

        service = TMDBService()
        user = CustomUser.objects.create_user(username="test", email="test@test.com", role="author")
        author = Author.objects.create(user=user, tmdb_id=123)

        service._download_and_save_author_photo(author, "/photo.jpg", 123)
        assert not author.photo or author.photo.name in ["", None]

    @patch("films.services.requests.get")
    def test_download_author_photo_no_names(self, mock_get):
        """Test author photo with no first/last name (fallback to username)."""
        mock_photo = MagicMock()
        mock_photo.status_code = 200
        mock_photo.content = b"photo_data"
        mock_get.return_value = mock_photo

        service = TMDBService()
        user = CustomUser.objects.create_user(
            username="testuser123", email="test@test.com", role="author", first_name="", last_name=""
        )
        author = Author.objects.create(user=user, tmdb_id=444)

        service._download_and_save_author_photo(author, "/photo.jpg", 444)
        assert "testuser123" in author.photo.name

    @patch("films.services.requests.get")
    def test_download_author_photo_only_first_name(self, mock_get):
        """Test author photo with only first name."""
        mock_photo = MagicMock()
        mock_photo.status_code = 200
        mock_photo.content = b"photo_data"
        mock_get.return_value = mock_photo

        service = TMDBService()
        user = CustomUser.objects.create_user(
            username="testuser", email="test@test.com", role="author", first_name="John", last_name=""
        )
        author = Author.objects.create(user=user, tmdb_id=333)

        service._download_and_save_author_photo(author, "/photo.jpg", 333)
        assert "john" in author.photo.name.lower()

    @patch("films.services.requests.get")
    def test_download_image_helper_success(self, mock_get):
        """Test _download_and_save_image helper method."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"image_data"
        mock_get.return_value = mock_resp

        service = TMDBService()
        film = Film(title="Test")

        service._download_and_save_image("https://example.com/image.jpg", film.poster, "test_poster.jpg")
        assert film.poster.name != ""

    @patch("films.services.requests.get")
    def test_download_image_helper_failure(self, mock_get):
        """Test _download_and_save_image with exception."""
        mock_get.side_effect = Exception("Download failed")

        service = TMDBService()
        film = Film(title="Test")

        service._download_and_save_image("https://example.com/image.jpg", film.poster, "test_poster.jpg")

    @patch("films.services.requests.get")
    def test_download_poster_deletes_old_file(self, mock_get):
        """Test that _download_and_save_poster replaces old file."""
        from django.core.files.base import ContentFile

        mock_poster = MagicMock()
        mock_poster.status_code = 200
        mock_poster.content = b"new_image_data"
        mock_get.return_value = mock_poster

        service = TMDBService()
        film = Film(title="Test Film", tmdb_id=456)

        film.poster.save("old_poster.jpg", ContentFile(b"old_data"), save=False)
        assert film.poster.name != ""

        service._download_and_save_poster(film, "/new_poster.jpg", 456)
        assert "test-film" in film.poster.name.lower()

    @patch("films.services.requests.get")
    def test_download_author_photo_deletes_old_file(self, mock_get):
        """Test that _download_and_save_author_photo replaces old file."""
        from django.core.files.base import ContentFile

        mock_photo = MagicMock()
        mock_photo.status_code = 200
        mock_photo.content = b"new_photo_data"
        mock_get.return_value = mock_photo

        service = TMDBService()
        user = CustomUser.objects.create_user(
            username="author_test", email="author@test.com", role="author", first_name="John", last_name="Doe"
        )
        author = Author.objects.create(user=user, tmdb_id=789)

        author.photo.save("old_photo.jpg", ContentFile(b"old_data"), save=False)
        assert author.photo.name != ""

        service._download_and_save_author_photo(author, "/new_photo.jpg", 789)
        assert "john" in author.photo.name.lower() or "doe" in author.photo.name.lower()


@pytest.mark.django_db
class TestTMDBServiceInit:
    """Tests for TMDBService initialization."""

    def test_tmdb_service_init_no_api_key(self):
        """Test TMDBService initialization without API key."""
        with patch("films.services.config") as mock_config:
            mock_config.return_value = ""
            service = TMDBService()
            assert service.api_key == ""
