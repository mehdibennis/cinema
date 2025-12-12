from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimestampedModelMixin


class Author(TimestampedModelMixin):

    SOURCE_CHOICES = [
        ("ADMIN", "Administration"),
        ("TMDB", "Import TMDb"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="author_profile",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)

    # Champs pour l'intégration TMDb
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="ADMIN")
    photo = models.ImageField(upload_to="author_photos/", null=True, blank=True)

    class Meta:
        verbose_name = "Auteur"
        verbose_name_plural = "Auteurs"
        ordering = ["user__last_name", "user__first_name"]

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return self.full_name

    def clean(self):
        """Ensure that only admins and authors can have an Author profile."""
        super().clean()
        if self.user and self.user.role == "spectator":
            raise ValidationError(
                {
                    "user": "A spectator cannot have an Author profile. "
                    "Only administrators and authors can be authors."
                }
            )

    def save(self, *args, **kwargs):
        """Override save to call clean() before saving."""
        self.clean()
        super().save(*args, **kwargs)


class AuthorReview(TimestampedModelMixin):
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey("spectators.Spectator", on_delete=models.CASCADE, related_name="author_reviews")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("author", "user")
        verbose_name = "Avis sur auteur"
        verbose_name_plural = "Avis sur auteurs"
        indexes = [
            # For listing reviews of an author sorted by date
            models.Index(fields=["author", "-created_at"], name="author_review_date_idx"),
        ]

    def __str__(self):
        return f"{self.user} - {self.author} ({self.rating}/5)"
