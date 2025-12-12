import factory

from authors.models import Author
from users.factories import UserFactory
from users.models import Role


class AuthorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Author

    user = factory.SubFactory(UserFactory, role=Role.AUTHOR)
    bio = factory.Faker("text")
    date_of_birth = factory.Faker("date_object")
