"""
Staff-only document access via pre-signed URLs.

Never exposes raw S3/B2 URLs. Staff click a link in the admin,
this view generates a 15-minute pre-signed URL and redirects to it.
For local development (filesystem storage), serves the file directly.
"""

import mimetypes

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponseRedirect

from ..models import Document


@staff_member_required
def document_view(request, document_id):
    """
    Generate a pre-signed URL for a document and redirect to it.

    GET /documents/<id>/view/

    - Staff-only (redirects to admin login if not authenticated)
    - S3/B2 backend: generates pre-signed URL with 15-min expiry, redirects
    - Local filesystem: serves the file directly via FileResponse
    """
    try:
        doc = Document.objects.select_related("application").get(pk=document_id)
    except Document.DoesNotExist:
        raise Http404("Document not found")

    if not doc.file:
        raise Http404("No file attached to this document")

    file_path = doc.file.name

    # S3 backend: generate pre-signed URL and redirect
    if hasattr(default_storage, "url"):
        try:
            url = default_storage.url(file_path)
            return HttpResponseRedirect(url)
        except Exception:
            # Fallback to direct file serve if URL generation fails
            pass

    # Local filesystem: serve directly
    if not default_storage.exists(file_path):
        raise Http404("File not found on storage")

    content_type, _ = mimetypes.guess_type(doc.original_filename or file_path)
    response = FileResponse(
        default_storage.open(file_path, "rb"),
        content_type=content_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'inline; filename="{doc.original_filename}"'
    return response
