from django.db import models

from core.models import TimestampedModelMixin


class Film(TimestampedModelMixin):
    STATUS_CHOICES = [
        ("draft", "Brouillon"),
        ("published", "Publié"),
        ("archived", "Archivé"),
    ]

    EVALUATION_CHOICES = [
        ("G", "Tout public"),
        ("PG", "Accord parental souhaitable"),
        ("PG-13", "Accord parental recommandé"),
        ("R", "Interdit aux moins de 17 ans"),
        ("NC-17", "Interdit aux moins de 18 ans"),
    ]

    SOURCE_CHOICES = [
        ("ADMIN", "Administration"),
        ("TMDB", "Import TMDb"),
    ]

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    release_date = models.DateField(db_index=True)
    evaluation = models.CharField(max_length=10, choices=EVALUATION_CHOICES, default="G")
    author = models.ForeignKey("authors.Author", on_delete=models.PROTECT, related_name="films")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", db_index=True)

    # Fields for TMDb integration
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="ADMIN")
    poster = models.ImageField(upload_to="film_posters/", null=True, blank=True)
    average_rating = models.FloatField(default=0.0, db_index=True)

    class Meta:
        verbose_name = "Film"
        verbose_name_plural = "Films"
        ordering = ["-release_date"]
        indexes = [
            # Composite indexes for common query patterns
            models.Index(fields=["status", "release_date"], name="film_status_date_idx"),
            models.Index(fields=["author", "status"], name="film_author_status_idx"),
            models.Index(fields=["author", "release_date"], name="film_author_release_idx"),
        ]

    def __str__(self):
        return self.title


class FilmReview(TimestampedModelMixin):
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey("spectators.Spectator", on_delete=models.CASCADE, related_name="film_reviews")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("film", "user")
        verbose_name = "Avis sur film"
        verbose_name_plural = "Avis sur films"
        indexes = [
            # For listing reviews of a film sorted by date (unique_together covers film lookup)
            models.Index(fields=["film", "-created_at"], name="review_film_date_idx"),
        ]

    def __str__(self):
        return f"{self.user} - {self.film} ({self.rating}/5)"
