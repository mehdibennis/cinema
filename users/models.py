from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from core.models import TimestampedModelMixin


class Role(models.TextChoices):
    AUTHOR = "author", "Auteur"
    SPECTATOR = "spectator", "Spectateur"
    ADMIN = "admin", "Administrateur"


class CustomUserManager(UserManager):
    """Custom manager to ensure create_superuser sets the role to ADMIN by default."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class CustomUser(TimestampedModelMixin, AbstractUser):
    objects: CustomUserManager = CustomUserManager()  # type: ignore[misc]

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SPECTATOR, db_index=True)

    def __str__(self):
        return self.username
