"""
URL configuration for GCLBA Application Portal.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView
from django_smartbase_admin.admin.site import sb_admin_site

urlpatterns = [
    path("admin/", sb_admin_site.urls),
    path("apply/", include("applications.urls")),
    path("", RedirectView.as_view(url="/apply/", permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
