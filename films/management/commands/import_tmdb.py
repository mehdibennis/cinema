from django.core.management.base import BaseCommand

from films.services import TMDBService


class Command(BaseCommand):
    help = "Import movies and authors from TMDb API"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10, help="Number of movies to import")

    def handle(self, *args, **options):
        limit = options["limit"]
        service = TMDBService()

        self.stdout.write(f"Fetching top {limit} popular movies...")
        movies = service.get_popular_movies(limit=limit)

        if not movies:
            self.stdout.write(self.style.WARNING("No movies found or API error."))
            return

        count = 0
        for movie_data in movies:
            self.stdout.write(f"Processing {movie_data.get('title')}...")
            film = service.import_movie(movie_data)
            if film:
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully imported {film.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Failed to import {movie_data.get('title')}"))

        self.stdout.write(self.style.SUCCESS(f"Finished! Imported {count} movies."))
