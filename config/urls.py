"""
URL configuration for GCLBA Application Portal.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView
from django_smartbase_admin.admin.site import sb_admin_site

from applications.views.admin_api import assign_to_me, pending_count, save_document_review
from applications.views.review_queue import (
    review_application,
    review_queue,
    review_update_status,
)

urlpatterns = [
    # Custom admin routes — BEFORE sb_admin_site.urls so they're not swallowed
    path("admin/review/", review_queue, name="review_queue"),
    path("admin/review/<int:pk>/", review_application, name="review_application"),
    path("admin/review/<int:pk>/update/", review_update_status, name="review_update_status"),
    path("admin/api/assign/<int:pk>/", assign_to_me, name="admin_assign_to_me"),
    path("admin/api/pending/", pending_count, name="admin_pending_count"),
    path("admin/api/doc-review/<int:pk>/", save_document_review, name="admin_doc_review"),
    path("admin/", sb_admin_site.urls),
    path("apply/", include("applications.urls")),
    path("", RedirectView.as_view(url="/apply/", permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
