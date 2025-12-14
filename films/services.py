import logging
from typing import Any

import requests
from decouple import config
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction

from authors.models import Author
from films.models import Film

logger = logging.getLogger(__name__)
User = get_user_model()


class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

    def __init__(self):
        self.api_key = config("TMDB_API_KEY", default="")
        if not self.api_key:
            logger.warning("TMDB_API_KEY is not set.")

    def get_popular_movies(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Fetch popular movies from TMDb.
        """
        if not self.api_key:
            return []

        try:
            response = requests.get(
                f"{self.BASE_URL}/movie/popular",
                params={"api_key": self.api_key, "language": "fr-FR"},
            )
            response.raise_for_status()
            return response.json().get("results", [])[:limit]
        except requests.RequestException as e:
            logger.error(f"Error fetching popular movies: {e}")
            return []

    @transaction.atomic
    def import_movie(self, movie_data: dict[str, Any]) -> Film | None:
        """
        Import a single movie and its director.
        """
        tmdb_id = movie_data.get("id")
        title = movie_data.get("title")
        release_date = movie_data.get("release_date")

        if not all([tmdb_id, title, release_date]):
            logger.warning(f"Skipping movie {title}: missing required data.")
            return None

        logger.info(f"Importing movie: {title} ({tmdb_id})")

        # Import Director first
        if tmdb_id is None:
            logger.warning(f"Missing tmdb_id for movie {title}, skipping.")
            return None
        director = self._fetch_and_import_director(tmdb_id)
        if not director:
            logger.warning(f"No director found for movie {title}, skipping.")
            return None

        # Create or Update Film
        film, created = Film.objects.update_or_create(
            tmdb_id=tmdb_id,
            defaults={
                "title": title,
                "description": movie_data.get("overview", ""),
                "release_date": release_date,
                "status": "published",
                "evaluation": "G",  # Default
                "source": "TMDB",
            },
        )

        # Add director to authors
        film.authors.add(director)

        # Handle Poster - always update if poster_path exists
        poster_path = movie_data.get("poster_path")
        if poster_path:
            self._download_and_save_poster(film, poster_path, tmdb_id)

        return film

    def _fetch_and_import_director(self, tmdb_id: int) -> Author | None:  # type: ignore[misc]
        """
        Fetch credits and import the first director found.
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/movie/{tmdb_id}/credits",
                params={"api_key": self.api_key},
            )
            response.raise_for_status()
            crew = response.json().get("crew", [])

            directors = [member for member in crew if member["job"] == "Director"]
            if directors:
                return self._import_author(directors[0])
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching credits for tmdb_id {tmdb_id}: {e}")
            return None

    def _import_author(self, person_data: dict[str, Any]) -> Author | None:
        """
        Import an author (director) from TMDb person data.
        Fetches additional details (birthday, bio) from the person endpoint.
        """
        tmdb_id = person_data.get("id")
        name = person_data.get("name")

        if not tmdb_id or not name:
            return None

        # Fetch full person details for birthday and biography
        person_details = self._fetch_person_details(tmdb_id)

        # Create User
        username = f"tmdb_{tmdb_id}"
        email = f"{username}@example.com"

        # Split name into first_name and last_name
        name_parts = name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": "author",
            },
        )
        if created:
            user.set_unusable_password()
            user.save()

        # Extract birthday from person details
        birthday = None
        if person_details and person_details.get("birthday"):
            try:
                from datetime import datetime

                birthday = datetime.strptime(person_details["birthday"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                birthday = None

        # Extract biography
        bio = ""
        if person_details:
            bio = person_details.get("biography", "") or ""

        # Create Author
        author, _ = Author.objects.update_or_create(
            user=user,
            defaults={
                "tmdb_id": tmdb_id,
                "source": "TMDB",
                "date_of_birth": birthday,
                "bio": bio[:1000] if bio else "",  # Limit bio length
            },
        )

        # Handle Photo - use profile_path from person_details if available
        profile_path = (person_details.get("profile_path") if person_details else None) or person_data.get(
            "profile_path"
        )
        if profile_path:
            self._download_and_save_author_photo(author, profile_path, tmdb_id)

        return author

    def _fetch_person_details(self, person_id: int) -> dict[str, Any] | None:
        """
        Fetch detailed person information from TMDb API.
        Returns birthday, biography, profile_path, etc.
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/person/{person_id}",
                params={"api_key": self.api_key, "language": "fr-FR"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Could not fetch person details for {person_id}: {e}")
            return None

    def _download_and_save_poster(self, film, poster_path: str, tmdb_id: int) -> None:
        """
        Download and save poster for a film, removing old file first.
        Uses film title for readable filename.
        """
        try:
            from django.utils.text import slugify

            url = f"{self.IMAGE_BASE_URL}{poster_path}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Delete old poster file if it exists
                if film.poster:
                    film.poster.delete(save=False)

                # Create clean filename from title
                clean_title = slugify(film.title)
                filename = f"poster_{clean_title}.jpg"

                # Save new poster with readable filename
                film.poster.save(filename, ContentFile(response.content), save=True)
        except Exception as e:
            logger.error(f"Failed to download poster for film {tmdb_id}: {e}")

    def _download_and_save_author_photo(self, author, profile_path: str, tmdb_id: int) -> None:
        """
        Download and save author photo, removing old file first.
        Uses author's first and last name for readable filename.
        """
        try:
            from django.utils.text import slugify

            url = f"{self.IMAGE_BASE_URL}{profile_path}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Delete old photo file if it exists
                if author.photo:
                    author.photo.delete(save=False)

                # Create clean filename from first and last name
                first_name = slugify(author.user.first_name) if author.user.first_name else ""
                last_name = slugify(author.user.last_name) if author.user.last_name else ""

                if first_name and last_name:
                    filename = f"author_{first_name}_{last_name}.jpg"
                elif first_name or last_name:
                    filename = f"author_{first_name or last_name}.jpg"
                else:
                    # Fallback to username if no name available
                    filename = f"author_{slugify(author.user.username)}.jpg"

                # Save new photo with readable filename
                author.photo.save(filename, ContentFile(response.content), save=True)
        except Exception as e:
            logger.error(f"Failed to download photo for author {tmdb_id}: {e}")

    def _download_and_save_image(self, url: str, model_field, filename: str) -> None:
        """
        Helper to download an image and save it to a model field.
        Deletes the old file first to prevent duplicates.
        """
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Delete old file if it exists to prevent duplicates
                if model_field and model_field.name:
                    model_field.delete(save=False)
                model_field.save(filename, ContentFile(response.content), save=True)
        except Exception as e:
            logger.error(f"Failed to download image {url}: {e}")
