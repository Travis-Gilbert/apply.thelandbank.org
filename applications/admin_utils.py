"""
Admin utility functions for the Unfold dashboard.

Provides:
- Dashboard stat cards (applications by status, recent submissions, property inventory)
- Personalized workload cards (my reviews, my waiting-on-docs)
- Queue health metrics (unassigned, stale applications)
- Environment badge (DEVELOPMENT / PRODUCTION)
- Sidebar badges showing pending review count and available property count
"""

from django.conf import settings

from applications.models import Application, Property


def environment_callback(request):
    """
    Show environment indicator in the admin header.
    Returns a dict with title and color.
    """
    if settings.DEBUG:
        return {
            "title": "Development",
            "color": "warning",
        }
    return {
        "title": "Production",
        "color": "success",
    }


def pending_count_badge(request):
    """
    Sidebar badge showing number of applications awaiting review.
    Returns a string to display, or empty string for no badge.
    """
    count = Application.objects.filter(status="received").count()
    if count > 0:
        return str(count)
    return ""


def available_properties_badge(request):
    """
    Sidebar badge showing number of available properties.
    Returns a string to display, or empty string for no badge.
    """
    count = Property.objects.filter(status="available").count()
    if count > 0:
        return str(count)
    return ""


def dashboard_callback(request, context):
    """
    Populate the admin dashboard with stat cards and recent activity.
    Called by Unfold's DASHBOARD_CALLBACK setting.

    Provides three layers of data:
    1. Global status counts and stat cards
    2. Personalized "my workload" for the logged-in staff member
    3. Queue health (unassigned, stale) and recent submissions table
    """
    from django.db.models import Count
    from django.utils import timezone

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
    received = status_counts.get("received", 0)
    under_review = status_counts.get("under_review", 0)
    approved = status_counts.get("approved", 0)
    declined = status_counts.get("declined", 0)
    needs_more_info = status_counts.get("needs_more_info", 0)

    # ── Queue health ──────────────────────────────────────────
    unassigned_received = Application.objects.filter(
        status="received",
        assigned_to__isnull=True,
    ).count()

    # Stale: received 5+ days ago (quick attention metric)
    stale_received = Application.objects.filter(
        status="received",
        submitted_at__lt=now - timezone.timedelta(days=5),
    ).count()

    # Stale: under review 14+ days (design doc metric for follow-up)
    stale_under_review = Application.objects.filter(
        status="under_review",
        updated_at__lte=now - timezone.timedelta(days=14),
    ).count()

    # ── Personalized workload ─────────────────────────────────
    my_apps = Application.objects.filter(assigned_to=request.user)
    my_review = my_apps.filter(status="under_review").count()
    my_needs_more_info = my_apps.filter(status="needs_more_info").count()

    # ── Recent submissions (last 7 days) ──────────────────────
    week_ago = now - timezone.timedelta(days=7)
    recent_count = Application.objects.filter(submitted_at__gte=week_ago).count()

    # Top 10 recent applications for the dashboard table
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

    context.update(
        {
            "greeting_time": greeting_time,
            # Stat card data (existing format for backwards compat)
            "stats": [
                {
                    "label": "Awaiting Review",
                    "value": received,
                    "icon": "pending_actions",
                    "color": "warning",
                    "link": "/admin/applications/application/?status__exact=received",
                },
                {
                    "label": "Under Review",
                    "value": under_review,
                    "icon": "rate_review",
                    "color": "info",
                    "link": "/admin/applications/application/?status__exact=under_review",
                },
                {
                    "label": "Needs More Info",
                    "value": needs_more_info,
                    "icon": "upload_file",
                    "color": "warning",
                    "link": "/admin/applications/application/?status__exact=needs_more_info",
                },
                {
                    "label": "Approved",
                    "value": approved,
                    "icon": "check_circle",
                    "color": "success",
                    "link": "/admin/applications/application/?status__exact=approved",
                },
                {
                    "label": "Declined",
                    "value": declined,
                    "icon": "cancel",
                    "color": "danger",
                    "link": "/admin/applications/application/?status__exact=declined",
                },
                {
                    "label": "Needs Reviewer",
                    "value": unassigned_received,
                    "icon": "person_off",
                    "color": "warning",
                    "link": "/admin/applications/application/?status__exact=received&assigned_to__isnull=True",
                },
                {
                    "label": "Stale (5+ Days)",
                    "value": stale_received,
                    "icon": "schedule",
                    "color": "danger",
                    "link": "/admin/applications/application/?status__exact=received",
                },
            ],
            # Global totals
            "total_applications": total,
            "needs_more_info": needs_more_info,
            "recent_week_count": recent_count,
            # Personalized workload (design doc Task 1)
            "unassigned": unassigned_received,
            "my_review": my_review,
            "my_needs_more_info": my_needs_more_info,
            "stale_under_review": stale_under_review,
            # Recent submissions table (expanded to 10, with full objects)
            "recent_applications": recent_apps,
            # Program breakdown
            "program_counts": program_counts,
            # Property inventory
            "property_stats": {
                "total_available": total_available,
                "by_program": property_counts,
                "unlisted_applications": unlisted_apps,
            },
        }
    )
    return context
