import factory
from django.contrib.auth import get_user_model

from users.models import Role

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = Role.SPECTATOR


class AuthorUserFactory(UserFactory):
    """Factory to create users with author role."""

    role = Role.AUTHOR


class AdminUserFactory(UserFactory):
    role = Role.ADMIN
    is_staff = True
    is_superuser = True
