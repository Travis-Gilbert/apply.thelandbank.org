"""
Staff-only document access and thumbnails for admin review.

Never exposes raw S3/B2 URLs to staff. The document view generates a pre-signed
URL (or streams locally in development). The thumbnail view renders a compact
preview image for image/PDF uploads used in the review queue UI.
"""

import mimetypes
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.utils.html import escape

from ..models import Document


def _get_document_or_404(document_id):
    try:
        return Document.objects.select_related("application").get(pk=document_id)
    except Document.DoesNotExist as exc:
        raise Http404("Document not found") from exc


def _thumbnail_placeholder(label):
    safe_label = escape(label[:12].upper())
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'>"
        "<rect x='1' y='1' width='158' height='158' rx='12' fill='#ffffff' stroke='#e5e7eb'/>"
        "<rect x='20' y='28' width='120' height='88' rx='8' fill='#f3f4f6'/>"
        "<text x='80' y='85' text-anchor='middle' font-family='sans-serif' "
        "font-size='20' font-weight='700' fill='#6b7280'>"
        f"{safe_label}"
        "</text>"
        "</svg>"
    ).encode("utf-8")


def _render_image_thumbnail(doc, size):
    with default_storage.open(doc.file.name, "rb") as src:
        with Image.open(src) as image:
            image = ImageOps.exif_transpose(image)
            has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            image.thumbnail((size, size), Image.Resampling.LANCZOS)

            output = BytesIO()
            if has_alpha:
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                image.save(output, format="PNG", optimize=True)
                return output.getvalue(), "image/png"

            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(output, format="JPEG", quality=82, optimize=True, progressive=True)
            return output.getvalue(), "image/jpeg"


def _render_pdf_thumbnail(doc, size):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    with default_storage.open(doc.file.name, "rb") as src:
        pdf_bytes = src.read()
    if not pdf_bytes:
        return None

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
            if pdf.page_count == 0:
                return None
            page = pdf[0]
            page_rect = page.rect
            longest_edge = max(page_rect.width, page_rect.height) or 1.0
            zoom = max(1.0, (size * 2) / longest_edge)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            return pixmap.tobytes("png"), "image/png"
    except Exception:
        return None


@staff_member_required
def document_view(request, document_id):
    """
    Generate a pre-signed URL for a document and redirect to it.

    GET /documents/<id>/view/

    - Staff-only (redirects to admin login if not authenticated)
    - S3/B2 backend: generates pre-signed URL with 15-min expiry, redirects
    - Local filesystem: serves the file directly via FileResponse
    """
    doc = _get_document_or_404(document_id)

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


@staff_member_required
def document_thumbnail(request, document_id):
    """
    Return a small preview image for a document.

    GET /documents/<id>/thumbnail/?size=160
    """
    doc = _get_document_or_404(document_id)
    if not doc.file:
        raise Http404("No file attached to this document")

    try:
        requested_size = int(request.GET.get("size", "160"))
    except (TypeError, ValueError):
        requested_size = 160
    size = max(64, min(requested_size, 512))

    cache_key = (
        f"doc-thumb:v1:{doc.pk}:{int(doc.uploaded_at.timestamp())}:{doc.file.name}:{size}"
    )
    cached = cache.get(cache_key)
    if cached:
        response = HttpResponse(cached["body"], content_type=cached["content_type"])
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    rendered = None
    try:
        if doc.is_image:
            rendered = _render_image_thumbnail(doc, size)
        elif doc.is_pdf:
            rendered = _render_pdf_thumbnail(doc, size)
    except (UnidentifiedImageError, OSError):
        rendered = None

    if rendered:
        body, content_type = rendered
    else:
        label = "PDF" if doc.is_pdf else "FILE"
        body = _thumbnail_placeholder(label)
        content_type = "image/svg+xml"

    cache.set(cache_key, {"body": body, "content_type": content_type}, 3600)
    response = HttpResponse(body, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response
