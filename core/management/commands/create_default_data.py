"""
Commande pour créer des données par défaut pour le développement et les tests.
Usage: python manage.py create_default_data
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from authors.models import Author
from films.models import Film, FilmReview
from spectators.models import Spectator
from users.models import CustomUser


class Command(BaseCommand):
    help = "Create default data (users, authors, films, spectators, reviews)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing data before creating new ones",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Deleting existing data..."))
            FilmReview.objects.all().delete()
            Film.objects.all().delete()
            Author.objects.all().delete()
            Spectator.objects.all().delete()
            CustomUser.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ Data deleted"))

        self.stdout.write(self.style.MIGRATE_HEADING("Creating data..."))

        # 1. Create admin user
        self._create_admin()

        # 2. Créer des auteurs
        authors = self._create_authors()

        # 3. Créer des films
        films = self._create_films(authors)

        # 4. Créer des spectateurs
        spectators = self._create_spectators()

        # 5. Créer des reviews
        self._create_reviews(spectators, films)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Data created successfully!\n"
                f"   - {CustomUser.objects.count()} users\n"
                f"   - {Author.objects.count()} authors\n"
                f"   - {Film.objects.count()} films\n"
                f"   - {Spectator.objects.count()} spectators\n"
                f"   - {FilmReview.objects.count()} reviews\n"
            )
        )

        self.stdout.write(
            self.style.HTTP_INFO(
                "\n📌 Login credentials:\n"
                "   Admin:      admin / admin123\n"
                "   Author:     spielberg / pass123\n"
                "   Spectator: cinephile / pass123\n"
            )
        )

    def _create_admin(self):
        """Create an admin account"""
        admin, created = CustomUser.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@cinema.com",
                "first_name": "Super",
                "last_name": "Admin",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(self.style.SUCCESS("✓ Admin créé"))
        return admin

    def _create_authors(self):
        """Create authors/directors"""
        authors_data = [
            {
                "username": "spielberg",
                "email": "steven@cinema.com",
                "first_name": "Steven",
                "last_name": "Spielberg",
                "bio": "Réalisateur américain légendaire, créateur de Jurassic Park et E.T.",
                "date_of_birth": "1946-12-18",
            },
            {
                "username": "nolan",
                "email": "chris@cinema.com",
                "first_name": "Christopher",
                "last_name": "Nolan",
                "bio": "Réalisateur britannique connu pour Inception et The Dark Knight.",
                "date_of_birth": "1970-07-30",
            },
            {
                "username": "tarantino",
                "email": "quentin@cinema.com",
                "first_name": "Quentin",
                "last_name": "Tarantino",
                "bio": "Réalisateur américain iconique de Pulp Fiction.",
                "date_of_birth": "1963-03-27",
            },
            {
                "username": "villeneuve",
                "email": "denis@cinema.com",
                "first_name": "Denis",
                "last_name": "Villeneuve",
                "bio": "Réalisateur canadien de Dune et Blade Runner 2049.",
                "date_of_birth": "1967-10-03",
            },
        ]

        authors = []
        for data in authors_data:
            user, created = CustomUser.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "role": "author",
                },
            )
            if created:
                user.set_password("pass123")
                user.save()

            author, created = Author.objects.get_or_create(
                user=user,
                defaults={
                    "bio": data["bio"],
                    "date_of_birth": data["date_of_birth"],
                    "source": "ADMIN",
                },
            )
            authors.append(author)

        self.stdout.write(self.style.SUCCESS(f"✓ {len(authors)} auteurs créés"))
        return authors

    def _create_films(self, authors):
        """Create films"""
        films_data = [
            {
                "title": "Jurassic Park",
                "description": "Un parc d'attractions peuplé de dinosaures clonés tourne au cauchemar.",
                "release_date": "1993-06-11",
                "evaluation": "PG-13",
                "status": "published",
                "author_idx": 0,  # Spielberg
            },
            {
                "title": "Inception",
                "description": "Un voleur qui s'infiltre dans les rêves pour voler des secrets.",
                "release_date": "2010-07-16",
                "evaluation": "PG-13",
                "status": "published",
                "author_idx": 1,  # Nolan
            },
            {
                "title": "Pulp Fiction",
                "description": "Histoires croisées de gangsters à Los Angeles.",
                "release_date": "1994-10-14",
                "evaluation": "R",
                "status": "published",
                "author_idx": 2,  # Tarantino
            },
            {
                "title": "Dune",
                "description": "L'histoire d'un jeune homme brillant sur une planète désertique.",
                "release_date": "2021-10-22",
                "evaluation": "PG-13",
                "status": "published",
                "author_idx": 3,  # Villeneuve
            },
            {
                "title": "The Dark Knight",
                "description": "Batman affronte le Joker dans une bataille épique pour Gotham.",
                "release_date": "2008-07-18",
                "evaluation": "PG-13",
                "status": "published",
                "author_idx": 1,  # Nolan
            },
            {
                "title": "Interstellar",
                "description": "Une équipe d'explorateurs voyage à travers un trou de ver spatial.",
                "release_date": "2014-11-07",
                "evaluation": "PG-13",
                "status": "published",
                "author_idx": 1,  # Nolan
            },
            {
                "title": "Django Unchained",
                "description": "Un esclave libéré part sauver sa femme des mains d'un propriétaire brutal.",
                "release_date": "2012-12-25",
                "evaluation": "R",
                "status": "published",
                "author_idx": 2,  # Tarantino
            },
            {
                "title": "E.T. l'extra-terrestre",
                "description": "Un jeune garçon se lie d'amitié avec un extraterrestre.",
                "release_date": "1982-06-11",
                "evaluation": "PG",
                "status": "published",
                "author_idx": 0,  # Spielberg
            },
        ]

        films = []
        for data in films_data:
            film, created = Film.objects.get_or_create(
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "release_date": data["release_date"],
                    "evaluation": data["evaluation"],
                    "status": data["status"],
                    "author": authors[data["author_idx"]],
                    "source": "ADMIN",
                },
            )
            films.append(film)

        self.stdout.write(self.style.SUCCESS(f"✓ {len(films)} films créés"))
        return films

    def _create_spectators(self):
        """Create spectators"""
        spectators_data = [
            {
                "username": "cinephile",
                "email": "cinephile@example.com",
                "first_name": "Marie",
                "last_name": "Dupont",
                "favorite_genre": "Science-Fiction",
            },
            {
                "username": "moviefan",
                "email": "moviefan@example.com",
                "first_name": "Jean",
                "last_name": "Martin",
                "favorite_genre": "Action",
            },
            {
                "username": "filmcritic",
                "email": "critic@example.com",
                "first_name": "Sophie",
                "last_name": "Bernard",
                "favorite_genre": "Drame",
            },
        ]

        spectators = []
        for data in spectators_data:
            user, created = CustomUser.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "role": "spectator",
                },
            )
            if created:
                user.set_password("pass123")
                user.save()

            spectator, created = Spectator.objects.get_or_create(
                user=user,
                defaults={
                    "favorite_genre": data["favorite_genre"],
                },
            )
            spectators.append(spectator)

        self.stdout.write(self.style.SUCCESS(f"✓ {len(spectators)} spectateurs créés"))
        return spectators

    def _create_reviews(self, spectators, films):
        """Create film reviews"""
        reviews_data = [
            # Cinephile (Marie)
            {
                "spectator_idx": 0,
                "film_idx": 1,
                "rating": 5,
                "comment": "Masterpiece! Inception is a film that pushes the boundaries of cinema.",
            },
            {
                "spectator_idx": 0,
                "film_idx": 3,
                "rating": 5,
                "comment": "Dune is a perfect adaptation, visually stunning.",
            },
            {
                "spectator_idx": 0,
                "film_idx": 5,
                "rating": 5,
                "comment": "Interstellar made me cry. A masterpiece.",
            },
            # Moviefan (Jean)
            {
                "spectator_idx": 1,
                "film_idx": 4,
                "rating": 5,
                "comment": "The Dark Knight redefines the superhero genre. The Joker is unforgettable.",
            },
            {
                "spectator_idx": 1,
                "film_idx": 0,
                "rating": 4,
                "comment": "Jurassic Park remains a timeless classic of adventure cinema.",
            },
            {
                "spectator_idx": 1,
                "film_idx": 6,
                "rating": 4,
                "comment": "Django is a brilliant modern western, with an outstanding performance.",
            },
            # Filmcritic (Sophie)
            {
                "spectator_idx": 2,
                "film_idx": 2,
                "rating": 5,
                "comment": "Pulp Fiction revolutionized narrative cinema. A Tarantino masterpiece.",
            },
            {
                "spectator_idx": 2,
                "film_idx": 7,
                "rating": 4,
                "comment": "E.T. retains all its magic after all these years. Guaranteed emotion.",
            },
            {
                "spectator_idx": 2,
                "film_idx": 1,
                "rating": 4,
                "comment": "Inception is intelligent and visually impressive.",
            },
        ]

        reviews = []
        for data in reviews_data:
            review, created = FilmReview.objects.get_or_create(
                user=spectators[data["spectator_idx"]],
                film=films[data["film_idx"]],
                defaults={
                    "rating": data["rating"],
                    "comment": data["comment"],
                },
            )
            if created:
                reviews.append(review)

        self.stdout.write(self.style.SUCCESS(f"✓ {len(reviews)} reviews created"))
        return reviews
