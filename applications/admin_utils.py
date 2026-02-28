"""
Admin utility functions — dashboard data queries.

These functions provide the query logic for dashboard statistics.
Originally built for Unfold callbacks; preserved as standalone helpers
for future SmartBase dashboard widgets.

Provides:
- Dashboard stat cards (applications by status, recent submissions, property inventory)
- Personalized workload cards (my reviews, my waiting-on-docs)
- Queue health metrics (unassigned, stale applications)
"""

from django.db.models import Count
from django.utils import timezone

from applications.models import Application, Property


def get_dashboard_stats(user):
    """
    Build dashboard statistics for the given staff user.

    Returns a dict with all the data needed for dashboard widgets:
    - greeting_time: morning / afternoon / evening
    - status_counts: dict of status → count
    - queue_health: unassigned, stale_received, stale_under_review
    - my_workload: my_review, my_needs_more_info counts
    - recent: count and queryset of last 7 days + top 10
    - program_counts: dict of program_type → count
    - property_stats: available inventory breakdown
    """
    now = timezone.now()

    # ── Time-of-day greeting ─────────────────────────────────
    hour = now.hour
    if hour < 12:
        greeting_time = "morning"
    elif hour < 17:
        greeting_time = "afternoon"
    else:
        greeting_time = "evening"

    # ── Global status counts ──────────────────────────────────
    status_counts = dict(
        Application.objects.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )

    total = Application.objects.count()

    # ── Queue health ──────────────────────────────────────────
    unassigned_received = Application.objects.filter(
        status="received",
        assigned_to__isnull=True,
    ).count()

    stale_received = Application.objects.filter(
        status="received",
        submitted_at__lt=now - timezone.timedelta(days=5),
    ).count()

    stale_under_review = Application.objects.filter(
        status="under_review",
        updated_at__lte=now - timezone.timedelta(days=14),
    ).count()

    # ── Personalized workload ─────────────────────────────────
    my_apps = Application.objects.filter(assigned_to=user)
    my_review = my_apps.filter(status="under_review").count()
    my_needs_more_info = my_apps.filter(status="needs_more_info").count()

    # ── Recent submissions (last 7 days) ──────────────────────
    week_ago = now - timezone.timedelta(days=7)
    recent_count = Application.objects.filter(submitted_at__gte=week_ago).count()
    recent_apps = (
        Application.objects.select_related("assigned_to")
        .order_by("-submitted_at")[:10]
    )

    # ── Program breakdown ─────────────────────────────────────
    program_counts = dict(
        Application.objects.values_list("program_type")
        .annotate(count=Count("id"))
        .values_list("program_type", "count")
    )

    # ── Property inventory ────────────────────────────────────
    property_counts = dict(
        Property.objects.filter(status=Property.Status.AVAILABLE)
        .values_list("program_type")
        .annotate(count=Count("id"))
        .values_list("program_type", "count")
    )
    total_available = sum(property_counts.values())
    unlisted_apps = Application.objects.filter(property_ref__isnull=True).count()

    return {
        "greeting_time": greeting_time,
        "total_applications": total,
        "status_counts": status_counts,
        "queue_health": {
            "unassigned": unassigned_received,
            "stale_received": stale_received,
            "stale_under_review": stale_under_review,
        },
        "my_workload": {
            "my_review": my_review,
            "my_needs_more_info": my_needs_more_info,
        },
        "recent": {
            "week_count": recent_count,
            "applications": recent_apps,
        },
        "program_counts": program_counts,
        "property_stats": {
            "total_available": total_available,
            "by_program": property_counts,
            "unlisted_applications": unlisted_apps,
        },
    }
