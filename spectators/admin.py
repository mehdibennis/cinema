from django.contrib import admin

from .models import Spectator


class FavoriteFilmInline(admin.TabularInline):
    """Inline to display a spectator's favorite films."""

    model = Spectator.favorite_films.through
    extra = 0
    verbose_name = "Film favori"
    verbose_name_plural = "Films favoris"
    autocomplete_fields = ["film"]


@admin.register(Spectator)
class SpectatorAdmin(admin.ModelAdmin):
    list_display = ("user", "favorite_genre", "films_favoris_count")
    search_fields = ("user__username", "user__email")
    list_filter = ("favorite_genre",)
    inlines = [FavoriteFilmInline]
    exclude = ("favorite_films",)  # Handle favorite films via inline

    @admin.display(description="Nb favoris")
    def films_favoris_count(self, obj):
        return obj.favorite_films.count()
