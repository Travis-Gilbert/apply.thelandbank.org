"""
Review Workflow Queue — focused one-at-a-time application review.

Staff work through a priority-ordered queue:
  1. Unassigned + received (oldest first)
  2. Assigned to me + received (oldest first)
  3. Assigned to me + under review (oldest first)

The queue view redirects to the first application, or shows an empty state.
Each application panel has an HTMX "Update & Next" button that saves the
status change and swaps to the next application in the queue.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from applications.models import Application, StatusLog


def _queue_queryset(user):
    """
    Return the review queue ordered by priority.

    Priority buckets:
      0 — Unassigned + received (most urgent)
      1 — Assigned to me + received
      2 — Assigned to me + under_review
      3 — Everything else active

    Within each bucket: oldest submitted_at first.
    """
    return (
        Application.objects.filter(
            status__in=[
                Application.Status.RECEIVED,
                Application.Status.UNDER_REVIEW,
                Application.Status.NEEDS_MORE_INFO,
            ]
        )
        .select_related("assigned_to")
        .prefetch_related("documents")
        .annotate(
            priority=Case(
                When(
                    assigned_to__isnull=True,
                    status=Application.Status.RECEIVED,
                    then=Value(0),
                ),
                When(
                    assigned_to=user,
                    status=Application.Status.RECEIVED,
                    then=Value(1),
                ),
                When(
                    assigned_to=user,
                    status=Application.Status.UNDER_REVIEW,
                    then=Value(2),
                ),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
        .order_by("priority", "submitted_at")
    )


@staff_member_required
def review_queue(request):
    """Redirect to the first application in the queue, or show empty state."""
    queue = _queue_queryset(request.user)
    first = queue.first()
    if first:
        return redirect("review_application", pk=first.pk)
    return render(request, "admin/review_queue/empty.html")


@staff_member_required
def review_application(request, pk):
    """Show a single application for review with queue navigation."""
    app = get_object_or_404(
        Application.objects.select_related("assigned_to").prefetch_related(
            "documents", "status_logs"
        ),
        pk=pk,
    )

    queue = _queue_queryset(request.user)
    queue_ids = list(queue.values_list("pk", flat=True)[:200])

    try:
        current_idx = queue_ids.index(app.pk)
        next_pk = queue_ids[current_idx + 1] if current_idx + 1 < len(queue_ids) else None
        prev_pk = queue_ids[current_idx - 1] if current_idx > 0 else None
        position = current_idx + 1
    except ValueError:
        next_pk = queue_ids[0] if queue_ids else None
        prev_pk = None
        position = 0

    # Calculate age
    days_open = (timezone.now() - app.submitted_at).days

    # Status choices for the dropdown
    allowed_transitions = Application.ALLOWED_TRANSITIONS.get(app.status, set())
    status_choices = [
        (s, label)
        for s, label in Application.Status.choices
        if s in allowed_transitions
    ]

    context = {
        "app": app,
        "queue_total": len(queue_ids),
        "position": position,
        "next_pk": next_pk,
        "prev_pk": prev_pk,
        "days_open": days_open,
        "status_choices": status_choices,
        "documents": list(app.documents.all()),
        "recent_logs": list(app.status_logs.select_related("changed_by").order_by("-changed_at")[:5]),
    }

    if request.headers.get("HX-Request"):
        return render(request, "admin/review_queue/_panel.html", context)
    return render(request, "admin/review_queue/review.html", context)


@staff_member_required
@require_http_methods(["POST"])
def review_update_status(request, pk):
    """
    HTMX endpoint: update status + claim + save note, then return next panel.
    """
    app = get_object_or_404(Application, pk=pk)
    new_status = request.POST.get("status", "").strip()
    note = request.POST.get("note", "").strip()

    errors = []

    # Auto-claim if unassigned
    if not app.assigned_to:
        app.assigned_to = request.user

    # Validate and apply status change
    if new_status and new_status != app.status:
        allowed = Application.ALLOWED_TRANSITIONS.get(app.status, set())
        if new_status not in allowed:
            old_label = dict(Application.Status.choices).get(app.status, app.status)
            new_label = dict(Application.Status.choices).get(new_status, new_status)
            errors.append(f"Cannot move from {old_label} to {new_label}.")
        else:
            old_status = app.status
            app.status = new_status
            app.save(update_fields=["status", "assigned_to", "updated_at"])

            StatusLog.objects.create(
                application=app,
                from_status=old_status,
                to_status=new_status,
                changed_by=request.user,
                notes=note or "",
            )
    else:
        # Just save the claim
        app.save(update_fields=["assigned_to", "updated_at"])

    if errors:
        return HttpResponse(
            f'<div class="text-red-600 font-semibold p-16">{"; ".join(errors)}</div>',
            status=422,
        )

    # Return the next application panel
    queue = _queue_queryset(request.user)
    next_app = queue.first()
    if next_app:
        return redirect("review_application", pk=next_app.pk)

    # Queue is empty
    return render(request, "admin/review_queue/empty.html")
