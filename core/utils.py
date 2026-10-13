from django.core.paginator import Paginator


def paginate(request, queryset, per_page=10):
    """Return the requested page (invalid page numbers fall back safely)."""
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))
