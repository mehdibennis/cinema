from django.conf import settings
from django.db import models

from core.models import TimestampedModelMixin


class Spectator(TimestampedModelMixin):
    GENRE_CHOICES = [
        ("action", "Action"),
        ("comedy", "Comédie"),
        ("drama", "Drame"),
        ("horror", "Horreur"),
        ("scifi", "Science-fiction"),
        ("romance", "Romance"),
        ("thriller", "Thriller"),
        ("animation", "Animation"),
        ("documentary", "Documentaire"),
        ("fantasy", "Fantastique"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="spectator_profile",
    )
    favorite_genre = models.CharField(
        max_length=20, choices=GENRE_CHOICES, blank=True, verbose_name="Genre préféré", db_index=True
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    favorite_films = models.ManyToManyField("films.Film", related_name="favorited_by", blank=True)

    class Meta:
        verbose_name = "Spectateur"
        verbose_name_plural = "Spectateurs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"], name="spectator_created_idx"),
        ]

    def __str__(self):
        return self.user.username
