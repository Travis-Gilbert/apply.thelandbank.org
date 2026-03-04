"""
Admin utility functions — dashboard data queries and SmartBase widgets.

Provides:
- get_dashboard_stats(): Query logic for all dashboard statistics
- DashboardStatsWidget: SmartBase dashboard widget that renders stats cards

Dashboard stat cards: applications by status, recent submissions, property inventory.
Personalized workload cards: my reviews, my waiting-on-docs.
Queue health metrics: unassigned, stale applications.
"""

from django.db.models import Count
from django.utils import timezone

from django_smartbase_admin.engine.dashboard import SBAdminDashboardWidget

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


# ── Status badge colors (match admin list view) ─────────────
STATUS_COLORS = {
    "received": "#3b82f6",       # blue
    "under_review": "#f59e0b",   # amber
    "approved": "#22c55e",       # green
    "declined": "#ef4444",       # red
    "needs_more_info": "#f97316",  # orange
}

# ── Human labels for program types ───────────────────────────
PROGRAM_LABELS = {
    "featured_homes": "Featured Homes",
    "ready_for_rehab": "Ready for Rehab",
    "vip_spotlight": "VIP Spotlight",
    "vacant_lot": "Vacant Lot",
}


class DashboardStatsWidget(SBAdminDashboardWidget):
    """
    Custom SmartBase dashboard widget that renders application statistics.

    Instead of using SmartBase's model-based chart/list widgets (which expect
    queryset annotation pipelines), this widget calls get_dashboard_stats()
    and renders the pre-computed data through a custom template.
    """

    template_name = "admin/dashboard/stats_widget.html"
    name = "dashboard_stats"

    def __init__(self):
        super().__init__(name=self.name, model=Application)

    def get_widget_context_data(self, request):
        context = super().get_widget_context_data(request)
        stats = get_dashboard_stats(request.user)

        # Build ordered status cards with colors
        status_cards = []
        for status_value, status_label in Application.Status.choices:
            status_cards.append({
                "label": status_label,
                "count": stats["status_counts"].get(status_value, 0),
                "color": STATUS_COLORS.get(status_value, "#6b7280"),
                "status_value": status_value,
            })

        # Build program breakdown cards
        program_cards = []
        for prog_value, prog_label in Application.ProgramType.choices:
            count = stats["program_counts"].get(prog_value, 0)
            if count > 0:
                program_cards.append({"label": prog_label, "count": count})

        # Build property inventory cards
        property_cards = []
        for prog_value in stats["property_stats"]["by_program"]:
            property_cards.append({
                "label": PROGRAM_LABELS.get(prog_value, prog_value),
                "count": stats["property_stats"]["by_program"][prog_value],
            })

        context.update({
            "stats": stats,
            "user": request.user,
            "status_cards": status_cards,
            "program_cards": program_cards,
            "property_cards": property_cards,
        })
        return context
