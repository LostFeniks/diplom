from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("api/", include("storage.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# React SPA fallback. API, media and static URLs must stay under Django control.
urlpatterns += [
    re_path(
        r"^(?!api/|media/|static/).*$",
        TemplateView.as_view(template_name="index.html"),
        name="spa",
    ),
]
