import factory

from films.models import Film, FilmReview
from spectators.factories import SpectatorFactory


class FilmFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Film

    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")
    release_date = factory.Faker("date_object")
    evaluation = "G"
    status = "published"

    @factory.lazy_attribute
    def author(self):
        from authors.factories import AuthorFactory

        return AuthorFactory()


class FilmReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FilmReview

    film = factory.SubFactory(FilmFactory)
    user = factory.SubFactory(SpectatorFactory)
    rating = factory.Faker("random_int", min=1, max=5)
    comment = factory.Faker("sentence")
