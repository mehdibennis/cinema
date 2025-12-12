import factory

from spectators.models import Spectator
from users.factories import UserFactory
from users.models import Role


class SpectatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Spectator

    user = factory.SubFactory(UserFactory, role=Role.SPECTATOR)
    favorite_genre = "Action"
    bio = factory.Faker("text")
