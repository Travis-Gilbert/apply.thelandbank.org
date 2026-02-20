"""
Admin utility functions for the Unfold dashboard.

Provides:
- Dashboard stat cards (applications by status, recent submissions)
- Environment badge (DEVELOPMENT / PRODUCTION)
- Sidebar badge showing pending review count
"""

from django.conf import settings

from applications.models import Application


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


def dashboard_callback(request, context):
    """
    Populate the admin dashboard with stat cards and recent activity.
    Called by Unfold's DASHBOARD_CALLBACK setting.
    """
    from django.db.models import Count
    from django.utils import timezone

    # Status counts
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

    # Queue health
    unassigned_received = Application.objects.filter(
        status="received",
        assigned_to__isnull=True,
    ).count()
    stale_received = Application.objects.filter(
        status="received",
        submitted_at__lt=timezone.now() - timezone.timedelta(days=5),
    ).count()

    # Recent submissions (last 7 days)
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent_count = Application.objects.filter(submitted_at__gte=week_ago).count()

    # Top 5 recent applications for quick access
    recent_apps = (
        Application.objects.order_by("-submitted_at")[:5]
        .values("id", "reference_number", "first_name", "last_name", "property_address", "status", "submitted_at")
    )

    context.update(
        {
            # Stat card data
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
                    "label": "Unassigned",
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
            "total_applications": total,
            "needs_more_info": needs_more_info,
            "recent_week_count": recent_count,
            "recent_applications": recent_apps,
        }
    )
    return context
