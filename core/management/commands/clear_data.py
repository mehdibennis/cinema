from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Clear development data (reviews, favorites, films, authors, spectators). Use --yes to execute."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Actually delete data")

    def handle(self, *args, **options):
        yes = options.get("yes")
        from django.contrib.auth import get_user_model

        from authors.models import Author, AuthorReview
        from films.models import Film, FilmReview
        from spectators.models import Spectator

        User = get_user_model()

        counts = {
            "film_reviews": FilmReview.objects.count(),
            "author_reviews": AuthorReview.objects.count(),
            "favorite_links": Spectator.favorite_films.through.objects.count(),
            "films": Film.objects.count(),
            "authors": Author.objects.count(),
            "spectators": Spectator.objects.count(),
            "users": User.objects.count(),
        }

        self.stdout.write("Current object counts:")
        for k, v in counts.items():
            self.stdout.write(f" - {k}: {v}")

        if not yes:
            self.stdout.write(self.style.WARNING("Dry run. No data will be deleted. Rerun with --yes to delete."))
            return

        with transaction.atomic():
            self.stdout.write("Deleting film reviews...")
            FilmReview.objects.all().delete()
            self.stdout.write("Deleting author reviews...")
            AuthorReview.objects.all().delete()
            self.stdout.write("Deleting favorite links (M2M)...")
            Spectator.favorite_films.through.objects.all().delete()
            self.stdout.write("Deleting films...")
            Film.objects.all().delete()
            self.stdout.write("Deleting authors...")
            Author.objects.all().delete()
            self.stdout.write("Deleting spectators...")
            Spectator.objects.all().delete()
            # Do NOT delete users by default to avoid removing superusers; if needed, user can run custom queries

        self.stdout.write(self.style.SUCCESS("Selected data cleared."))
