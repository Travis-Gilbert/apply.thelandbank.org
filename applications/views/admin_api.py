"""
Lightweight HTMX/JSON API endpoints for admin interactions.

These views handle:
- Claim/assign an application to the current staff user
- Return pending count for sidebar badge polling
- Per-document review status (ok/flagged/pending)
"""

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from django.views.decorators.http import require_http_methods

from applications.models import Application


@staff_member_required
@require_http_methods(["POST"])
def assign_to_me(request, pk):
    """
    HTMX endpoint: assign an application to the current user.

    Returns an HTML fragment replacing the Claim button with the reviewer name.
    """
    app = get_object_or_404(Application, pk=pk)

    if app.assigned_to and app.assigned_to != request.user:
        name = app.assigned_to.get_full_name() or app.assigned_to.get_username()
        return HttpResponse(
            format_html(
                '<span class="text-amber-600 text-13 font-medium">'
                "Already assigned to {}</span>",
                name,
            ),
            status=200,
        )

    app.assigned_to = request.user
    app.save(update_fields=["assigned_to", "updated_at"])

    name = request.user.get_full_name() or request.user.get_username()
    return HttpResponse(
        format_html(
            '<span class="text-13 font-medium text-dark-700">{}</span>',
            name,
        )
    )


@staff_member_required
def pending_count(request):
    """
    JSON endpoint: return count of applications needing review.

    Polled by the sidebar badge every 60 seconds.
    """
    count = Application.objects.filter(
        status__in=[
            Application.Status.RECEIVED,
            Application.Status.NEEDS_MORE_INFO,
        ]
    ).count()

    return JsonResponse({"count": count})


VALID_DOC_STATUSES = {"ok", "flagged", "pending"}


@staff_member_required
@require_http_methods(["POST"])
def save_document_review(request, pk):
    """
    JSON endpoint: save per-document review status on an application.

    Accepts JSON body: {"doc_id": "123", "status": "ok"|"flagged"|"pending"}
    Stores in Application.document_review JSONField keyed by doc PK.
    """
    app = get_object_or_404(Application, pk=pk)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    doc_id = str(body.get("doc_id", ""))
    status = body.get("status", "")

    if not doc_id or status not in VALID_DOC_STATUSES:
        return JsonResponse(
            {"error": "doc_id and status (ok/flagged/pending) required"},
            status=400,
        )

    # Verify document belongs to this application
    if not app.documents.filter(pk=doc_id).exists():
        return JsonResponse({"error": "Document not found"}, status=404)

    review = app.document_review or {}
    review[doc_id] = status
    app.document_review = review
    app.save(update_fields=["document_review", "updated_at"])

    return JsonResponse({"ok": True, "doc_id": doc_id, "status": status})


@staff_member_required
@require_http_methods(["GET", "POST"])
def import_properties_csv(request):
    """
    Admin view: upload a CSV or Excel file to import available properties.

    GET:  renders upload form
    POST: processes file via csv_import module, renders results
    """
    from applications.csv_import import (
        import_properties_from_csv,
        import_properties_from_excel,
    )

    result = None
    error = None

    if request.method == "POST":
        uploaded = request.FILES.get("file")
        replace_existing = request.POST.get("replace_existing") == "on"
        batch_label = request.POST.get("batch_label", "").strip()

        if not uploaded:
            error = "Please select a file to upload."
        else:
            filename = uploaded.name.lower()
            if filename.endswith((".xlsx", ".xls", ".xlsm")):
                result = import_properties_from_excel(
                    uploaded,
                    replace_existing=replace_existing,
                    batch_label=batch_label or "",
                )
            elif filename.endswith(".csv"):
                result = import_properties_from_csv(
                    uploaded,
                    replace_existing=replace_existing,
                    batch_label=batch_label or "",
                )
            else:
                error = "Unsupported file type. Please upload a .csv or .xlsx file."

    return render(request, "admin/property_import_csv.html", {
        "result": result,
        "error": error,
    })
