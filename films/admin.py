from django.contrib import admin
from django.utils.html import format_html

from .models import Film, FilmReview


class FilmReviewInline(admin.TabularInline):
    model = FilmReview
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = (
        "poster_thumbnail",
        "title",
        "release_date",
        "evaluation",
        "status",
        "source",
        "average_rating_display",
    )
    list_filter = ("created_at", "evaluation", "status", "source")
    search_fields = ("title", "description")
    autocomplete_fields = ("authors",)
    inlines = [FilmReviewInline]
    readonly_fields = ("created_at", "updated_at", "poster_preview")

    @admin.display(description="Poster")
    def poster_thumbnail(self, obj):
        """Display a thumbnail of the poster in the list view."""
        if obj.poster:
            return format_html(
                '<img src="{}" style="width: 50px; height: 75px; object-fit: cover;" />',
                obj.poster.url,
            )
        return "-"

    @admin.display(description="Poster preview")
    def poster_preview(self, obj):
        """Display a larger preview of the poster in the detail view."""
        if obj.poster:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 450px;" />',
                obj.poster.url,
            )
        return "No poster"

    @admin.display(description="Average rating")
    def average_rating_display(self, obj):
        # Calculate the average rating
        reviews = obj.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / reviews.count()
        return "-"


@admin.register(FilmReview)
class FilmReviewAdmin(admin.ModelAdmin):
    list_display = ("film", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("film__title", "user__user__username")
