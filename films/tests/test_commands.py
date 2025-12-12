from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from films.models import Film


@pytest.mark.django_db
class TestImportTMDBCommand:

    @patch("films.management.commands.import_tmdb.TMDBService")
    def test_import_tmdb_command_success(self, MockTMDBService):
        # Setup mock
        mock_service = MockTMDBService.return_value
        mock_service.get_popular_movies.return_value = [
            {"id": 1, "title": "Movie 1"},
            {"id": 2, "title": "Movie 2"},
        ]

        # Mock import_movie to return a Film object or None
        film1 = MagicMock(spec=Film)
        film1.title = "Movie 1"

        # First call returns film1, second call returns None (simulating failure)
        mock_service.import_movie.side_effect = [film1, None]

        # Run command
        call_command("import_tmdb", limit=2)

        # Assertions
        mock_service.get_popular_movies.assert_called_once_with(limit=2)
        assert mock_service.import_movie.call_count == 2

    @patch("films.management.commands.import_tmdb.TMDBService")
    def test_import_tmdb_command_no_movies(self, MockTMDBService):
        # Setup mock
        mock_service = MockTMDBService.return_value
        mock_service.get_popular_movies.return_value = []

        # Run command
        call_command("import_tmdb")

        # Assertions
        mock_service.get_popular_movies.assert_called_once()
        mock_service.import_movie.assert_not_called()
