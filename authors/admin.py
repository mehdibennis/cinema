from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Author, AuthorReview


class AuthorReviewInline(admin.TabularInline):
    model = AuthorReview
    extra = 0
    readonly_fields = ("created_at",)


class FilmInline(admin.TabularInline):
    from films.models import Film

    model = Film
    fk_name = "author"
    extra = 0
    fields = ("title", "release_date", "status", "evaluation")
    readonly_fields = ("title", "release_date", "status", "evaluation")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class HasFilmFilter(admin.SimpleListFilter):
    title = "A des films"
    parameter_name = "has_films"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Oui"),
            ("no", "Non"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.annotate(num_films=Count("films")).filter(num_films__gt=0)
        if self.value() == "no":
            return queryset.annotate(num_films=Count("films")).filter(num_films=0)
        return queryset


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = (
        "photo_thumbnail",
        "full_name",
        "username",
        "date_of_birth",
        "source",
        "count_films",
    )
    list_filter = (HasFilmFilter, "source")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "bio",
    )
    autocomplete_fields = ("user",)
    inlines = [FilmInline, AuthorReviewInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit the choice of users to admins and authors only."""
        if db_field.name == "user":
            from users.models import CustomUser

            kwargs["queryset"] = CustomUser.objects.filter(role__in=["admin", "author"]).exclude(
                author_profile__isnull=False
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Photo")
    def photo_thumbnail(self, obj):
        """Display a thumbnail of the photo in the list."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                obj.photo.url,
            )
        return "-"

    @admin.display(description="Photo preview")
    def photo_preview(self, obj):
        """Display a larger preview of the photo in the detail view."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px;" />',
                obj.photo.url,
            )
        return "No photo"

    @admin.display(description="Full name", ordering="user__last_name")
    def full_name(self, obj):
        """Display the full name (first name + last name) instead of the username."""
        first = obj.user.first_name or ""
        last = obj.user.last_name or ""
        full = f"{first} {last}".strip()
        return full if full else obj.user.username

    @admin.display(description="Username")
    def username(self, obj):
        return obj.user.username

    @admin.display(description="Number of films")
    def count_films(self, obj):
        return obj.films.count()

    # To display the list of films in the detail view (read-only or via a custom inline if needed)
    # Here we use a method to display the titles in the form
    readonly_fields = ("full_name", "display_films", "photo_preview")

    @admin.display(description="Associated films")
    def display_films(self, obj):
        return ", ".join([film.title for film in obj.films.all()])


@admin.register(AuthorReview)
class AuthorReviewAdmin(admin.ModelAdmin):
    list_display = ("author", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("author__user__username", "user__user__username")
