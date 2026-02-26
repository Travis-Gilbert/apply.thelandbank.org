# 003: Staff Admin Dashboard UX Upgrades

**Scope:** Unfold admin enhancements, custom dashboard view, status timeline, batch actions, workflow speed improvements.
**Depends on:** 001 (infrastructure)
**Estimated tasks:** 10

## Design Intent

Staff are coming from a workflow where applications arrived as PDF attachments in a shared email inbox. Someone would print the PDF, review it, write notes in the margins, and file it in a physical folder. Status updates happened via email chains and a shared spreadsheet.

Every admin screen needs to answer the question: "What do I need to do right now?" faster than the old system did. The previous system required staff to open an email, find the PDF, read through it, check the spreadsheet for status, then decide what to do. The portal should collapse that entire sequence into a single screen with clear actions.

The admin already has Django Unfold with colored status badges, organized fieldsets, inline documents, and audit trail. This doc extends that foundation with workflow-specific improvements.

## Task 1: Add a Custom Staff Dashboard Page

**Purpose:** Replace the default Unfold "Recent Actions" landing page with a purpose-built dashboard that shows what needs attention right now.

**File:** `applications/views.py`

Add a new view:

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone


@staff_member_required
def staff_dashboard(request):
    """
    Custom staff landing page showing workload at a glance.

    Replaces the default admin index with actionable metrics:
    how many applications need review, how many are waiting on
    documents, and who has what assigned.
    """
    now = timezone.now()
    seven_days_ago = now - timezone.timedelta(days=7)

    # Status counts
    status_counts = dict(
        Application.objects.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )

    # Applications needing action (submitted, no one assigned)
    unassigned = Application.objects.filter(
        status=Application.Status.SUBMITTED,
        assigned_to__isnull=True,
    ).count()

    # My assigned applications (for the logged-in staff member)
    my_apps = Application.objects.filter(assigned_to=request.user)
    my_review = my_apps.filter(status=Application.Status.UNDER_REVIEW).count()
    my_docs_requested = my_apps.filter(status=Application.Status.DOCS_REQUESTED).count()

    # Recent submissions (last 7 days)
    recent = Application.objects.filter(
        submitted_at__gte=seven_days_ago
    ).order_by("-submitted_at")[:10]

    # Stale applications (under review for > 14 days)
    fourteen_days_ago = now - timezone.timedelta(days=14)
    stale = Application.objects.filter(
        status=Application.Status.UNDER_REVIEW,
        updated_at__lte=fourteen_days_ago,
    ).count()

    # Program breakdown
    program_counts = dict(
        Application.objects.values_list("program_type")
        .annotate(count=Count("id"))
        .values_list("program_type", "count")
    )

    context = {
        "status_counts": status_counts,
        "unassigned": unassigned,
        "my_review": my_review,
        "my_docs_requested": my_docs_requested,
        "recent": recent,
        "stale": stale,
        "program_counts": program_counts,
        "total": Application.objects.count(),
    }
    return render(request, "admin/staff_dashboard.html", context)
```

---

## Task 2: Create the Staff Dashboard Template

**File:** `templates/admin/staff_dashboard.html`

```html
{% extends "admin/base_site.html" %}
{% load i18n %}

{% block title %}Dashboard{% endblock %}
{% block content_title %}{% endblock %}

{% block content %}
<div style="max-width: 1200px; margin: 0 auto;">

  {# ---- Greeting + summary ---- #}
  <div style="margin-bottom: 32px;">
    <h1 style="font-size: 24px; font-weight: 700; color: #111; margin: 0 0 8px;">
      Good {% now "A" %}, {{ request.user.first_name|default:request.user.username }}
    </h1>
    <p style="font-size: 14px; color: #6b7280; margin: 0;">
      {{ total }} total application{{ total|pluralize }} in the system.
      {% if unassigned %}
        <strong style="color: #dc2626;">{{ unassigned }} unassigned</strong> need{{ unassigned|pluralize:"s," }} attention.
      {% else %}
        All applications are assigned.
      {% endif %}
    </p>
  </div>

  {# ---- Stat cards ---- #}
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px;">

    {# Needs Action #}
    <a href="{% url 'admin:applications_application_changelist' %}?status__exact=submitted&assigned_to__isnull=True"
       style="text-decoration: none;">
      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 20px;">
        <p style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #991b1b; margin: 0 0 4px;">
          Needs Action
        </p>
        <p style="font-size: 32px; font-weight: 800; color: #dc2626; margin: 0;">
          {{ unassigned }}
        </p>
        <p style="font-size: 11px; color: #9ca3af; margin: 4px 0 0;">Unassigned submissions</p>
      </div>
    </a>

    {# My Review Queue #}
    <a href="{% url 'admin:applications_application_changelist' %}?status__exact=under_review&assigned_to__id__exact={{ request.user.pk }}"
       style="text-decoration: none;">
      <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 20px;">
        <p style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #92400e; margin: 0 0 4px;">
          My Reviews
        </p>
        <p style="font-size: 32px; font-weight: 800; color: #d97706; margin: 0;">
          {{ my_review }}
        </p>
        <p style="font-size: 11px; color: #9ca3af; margin: 4px 0 0;">Under review by you</p>
      </div>
    </a>

    {# Docs Requested #}
    <a href="{% url 'admin:applications_application_changelist' %}?status__exact=docs_requested&assigned_to__id__exact={{ request.user.pk }}"
       style="text-decoration: none;">
      <div style="background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 8px; padding: 20px;">
        <p style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #5b21b6; margin: 0 0 4px;">
          Waiting on Docs
        </p>
        <p style="font-size: 32px; font-weight: 800; color: #7c3aed; margin: 0;">
          {{ my_docs_requested }}
        </p>
        <p style="font-size: 11px; color: #9ca3af; margin: 4px 0 0;">Buyer needs to upload</p>
      </div>
    </a>

    {# Stale #}
    {% if stale %}
    <div style="background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 20px;">
      <p style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #9a3412; margin: 0 0 4px;">
        Stale (14+ days)
      </p>
      <p style="font-size: 32px; font-weight: 800; color: #ea580c; margin: 0;">
        {{ stale }}
      </p>
      <p style="font-size: 11px; color: #9ca3af; margin: 4px 0 0;">Need follow-up</p>
    </div>
    {% endif %}
  </div>

  {# ---- Recent submissions table ---- #}
  <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
    <div style="padding: 16px 20px; border-bottom: 1px solid #f3f4f6;">
      <h2 style="font-size: 14px; font-weight: 700; color: #111; margin: 0;">
        Recent Submissions (Last 7 Days)
      </h2>
    </div>
    <table style="width: 100%; border-collapse: collapse;">
      <thead>
        <tr style="background: #f9fafb;">
          <th style="padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280;">Ref #</th>
          <th style="padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280;">Applicant</th>
          <th style="padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280;">Property</th>
          <th style="padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280;">Program</th>
          <th style="padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280;">Status</th>
          <th style="padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280;">Assigned</th>
        </tr>
      </thead>
      <tbody>
        {% for app in recent %}
        <tr style="border-top: 1px solid #f3f4f6;">
          <td style="padding: 12px 16px;">
            <a href="{% url 'admin:applications_application_change' app.pk %}"
               style="font-size: 13px; font-weight: 600; color: #16a34a; text-decoration: none;">
              {{ app.reference_number }}
            </a>
          </td>
          <td style="padding: 12px 16px; font-size: 13px; color: #374151;">
            {{ app.full_name }}
          </td>
          <td style="padding: 12px 16px; font-size: 13px; color: #6b7280;">
            {{ app.property_address|truncatechars:35 }}
          </td>
          <td style="padding: 12px 16px; font-size: 12px; color: #6b7280;">
            {{ app.get_program_type_display }}
          </td>
          <td style="padding: 12px 16px;">
            <span style="
              display: inline-block; padding: 2px 10px; border-radius: 9999px;
              font-size: 11px; font-weight: 600;
              {% if app.status == 'submitted' %}background: #dbeafe; color: #1e40af;
              {% elif app.status == 'under_review' %}background: #fef3c7; color: #92400e;
              {% elif app.status == 'docs_requested' %}background: #ede9fe; color: #5b21b6;
              {% elif app.status == 'approved' %}background: #dcfce7; color: #166534;
              {% elif app.status == 'denied' %}background: #fee2e2; color: #991b1b;
              {% else %}background: #f3f4f6; color: #6b7280;{% endif %}
            ">
              {{ app.get_status_display }}
            </span>
          </td>
          <td style="padding: 12px 16px; font-size: 13px; color: #6b7280;">
            {{ app.assigned_to.get_short_name|default:"Unassigned" }}
          </td>
        </tr>
        {% empty %}
        <tr>
          <td colspan="6" style="padding: 24px 16px; text-align: center; color: #9ca3af; font-size: 13px;">
            No submissions in the last 7 days.
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

</div>
{% endblock %}
```

---

## Task 3: Wire the Dashboard into Unfold

**File:** `config/settings.py`

Add the dashboard URL to the Unfold config:

```python
UNFOLD = {
    "SITE_TITLE": "GCLBA Application Portal",
    "SITE_HEADER": "GCLBA",
    "DASHBOARD_CALLBACK": "applications.views.staff_dashboard",
    "SIDEBAR": {
        "navigation": [
            {
                "title": "Applications",
                "items": [
                    {
                        "title": "Dashboard",
                        "link": "/admin/",
                        "icon": "dashboard",
                    },
                    {
                        "title": "All Applications",
                        "link": "/admin/applications/application/",
                        "icon": "description",
                    },
                    {
                        "title": "Drafts (In Progress)",
                        "link": "/admin/applications/applicationdraft/",
                        "icon": "edit_note",
                    },
                ],
            },
        ],
    },
}
```

**File:** `config/urls.py`

Add the dashboard URL:

```python
from applications.views import staff_dashboard

urlpatterns = [
    path("admin/dashboard/", staff_dashboard, name="staff-dashboard"),
    path("admin/", admin.site.urls),
    # ... rest of urls
]
```

**Verify:** Visit `/admin/`. The dashboard should show stat cards and recent submissions instead of the default "Recent Actions" widget.

---

## Task 4: Add Visual Status Timeline to Application Detail

**Purpose:** When a staff member opens an application, they should immediately see the full history of what happened, not just the current status. This replaces the tabular `StatusLogInline` with a visual timeline.

**File:** `templates/admin/applications/application/change_form.html`

Create this template to override Unfold's default change form for Application:

```html
{% extends "admin/change_form.html" %}

{% block after_field_sets %}
{{ block.super }}

{# ---- Status Timeline ---- #}
{% if original %}
<div style="margin: 24px 0; padding: 24px; background: white; border: 1px solid #e5e7eb; border-radius: 8px;">
  <h3 style="font-size: 14px; font-weight: 700; color: #111; margin: 0 0 16px;">
    Application Timeline
  </h3>

  <div style="position: relative; padding-left: 24px;">
    {# Vertical line #}
    <div style="position: absolute; left: 7px; top: 4px; bottom: 4px; width: 2px; background: #e5e7eb;"></div>

    {# Submission event (always first) #}
    <div style="position: relative; margin-bottom: 20px;">
      <div style="position: absolute; left: -24px; top: 2px; width: 16px; height: 16px; border-radius: 50%; background: #16a34a; border: 3px solid white; box-shadow: 0 0 0 2px #16a34a;"></div>
      <div>
        <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">
          Application Submitted
        </p>
        <p style="font-size: 12px; color: #6b7280; margin: 2px 0 0;">
          {{ original.submitted_at|date:"M j, Y \a\t g:i A" }}
          &middot; {{ original.full_name }}
          &middot; {{ original.get_program_type_display }}
        </p>
      </div>
    </div>

    {# Status change events #}
    {% for log in original.status_logs.all %}
    <div style="position: relative; margin-bottom: 20px;">
      <div style="
        position: absolute; left: -24px; top: 2px;
        width: 16px; height: 16px; border-radius: 50%;
        border: 3px solid white;
        {% if log.to_status == 'approved' %}background: #16a34a; box-shadow: 0 0 0 2px #16a34a;
        {% elif log.to_status == 'denied' %}background: #dc2626; box-shadow: 0 0 0 2px #dc2626;
        {% elif log.to_status == 'docs_requested' %}background: #7c3aed; box-shadow: 0 0 0 2px #7c3aed;
        {% elif log.to_status == 'under_review' %}background: #d97706; box-shadow: 0 0 0 2px #d97706;
        {% else %}background: #6b7280; box-shadow: 0 0 0 2px #6b7280;{% endif %}
      "></div>
      <div>
        <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">
          {{ log.get_from_status_display|default:"New" }}
          &rarr;
          {{ log.get_to_status_display }}
        </p>
        <p style="font-size: 12px; color: #6b7280; margin: 2px 0 0;">
          {{ log.changed_at|date:"M j, Y \a\t g:i A" }}
          {% if log.changed_by %}&middot; {{ log.changed_by.get_short_name }}{% endif %}
        </p>
        {% if log.notes %}
        <p style="font-size: 12px; color: #374151; margin: 6px 0 0; padding: 8px 12px; background: #f9fafb; border-radius: 6px; border-left: 3px solid #e5e7eb;">
          {{ log.notes }}
        </p>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
{% endif %}
{% endblock %}
```

**Verify:** Open any application in the admin. The timeline should appear below the fieldsets, showing submission date and all status changes with colored dots.

---

## Task 5: Add Batch Status Actions

**Purpose:** Staff should be able to select multiple applications in the list view and change their status in bulk (e.g. move 5 new submissions to "Under Review" at once, or assign them all to a reviewer).

**File:** `applications/admin.py`

Add batch actions to `ApplicationAdmin`:

```python
from django.contrib import messages


def make_under_review(modeladmin, request, queryset):
    """Move selected applications to Under Review status."""
    updated = 0
    for app in queryset.filter(status=Application.Status.SUBMITTED):
        old_status = app.status
        app.status = Application.Status.UNDER_REVIEW
        if not app.assigned_to:
            app.assigned_to = request.user
        app.save()
        StatusLog.objects.create(
            application=app,
            from_status=old_status,
            to_status=Application.Status.UNDER_REVIEW,
            changed_by=request.user,
            notes="Batch action: moved to review",
        )
        updated += 1
    messages.success(request, f"{updated} application(s) moved to Under Review.")

make_under_review.short_description = "Move to Under Review (and assign to me)"


def request_documents(modeladmin, request, queryset):
    """Move selected applications to Documents Requested."""
    updated = 0
    for app in queryset.exclude(status__in=[
        Application.Status.APPROVED,
        Application.Status.DENIED,
    ]):
        old_status = app.status
        app.status = Application.Status.DOCS_REQUESTED
        app.save()
        StatusLog.objects.create(
            application=app,
            from_status=old_status,
            to_status=Application.Status.DOCS_REQUESTED,
            changed_by=request.user,
            notes="Batch action: documents requested",
        )
        updated += 1
    messages.success(request, f"{updated} application(s) marked as Documents Requested.")

request_documents.short_description = "Request Documents"


def assign_to_me(modeladmin, request, queryset):
    """Assign selected applications to the current user."""
    updated = queryset.filter(assigned_to__isnull=True).update(assigned_to=request.user)
    messages.success(request, f"{updated} application(s) assigned to you.")

assign_to_me.short_description = "Assign to me"
```

Add these to `ApplicationAdmin`:

```python
@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    actions = [make_under_review, request_documents, assign_to_me]
    # ... rest of existing config
```

**Verify:** In the admin list view, select multiple applications. The action dropdown should show the three new options.

---

## Task 6: Add Quick Filters to List View

**Purpose:** Staff need to quickly see "my applications," "unassigned," and "stale" without manually combining filters.

**File:** `applications/admin.py`

Add custom list filters:

```python
from django.utils import timezone


class AssignmentFilter(admin.SimpleListFilter):
    title = "assignment"
    parameter_name = "assignment"

    def lookups(self, request, model_admin):
        return [
            ("mine", "Assigned to me"),
            ("unassigned", "Unassigned"),
            ("others", "Assigned to others"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "mine":
            return queryset.filter(assigned_to=request.user)
        if self.value() == "unassigned":
            return queryset.filter(assigned_to__isnull=True)
        if self.value() == "others":
            return queryset.filter(
                assigned_to__isnull=False
            ).exclude(assigned_to=request.user)
        return queryset


class FreshnessFilter(admin.SimpleListFilter):
    title = "freshness"
    parameter_name = "freshness"

    def lookups(self, request, model_admin):
        return [
            ("today", "Submitted today"),
            ("week", "This week"),
            ("stale", "Stale (14+ days in review)"),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "today":
            return queryset.filter(submitted_at__date=now.date())
        if self.value() == "week":
            week_ago = now - timezone.timedelta(days=7)
            return queryset.filter(submitted_at__gte=week_ago)
        if self.value() == "stale":
            cutoff = now - timezone.timedelta(days=14)
            return queryset.filter(
                status=Application.Status.UNDER_REVIEW,
                updated_at__lte=cutoff,
            )
        return queryset
```

Update `ApplicationAdmin.list_filter`:

```python
list_filter = (
    AssignmentFilter,
    FreshnessFilter,
    "status",
    "program_type",
    "purchase_type",
    "submitted_at",
)
```

---

## Task 7: Add Document Completeness Indicator

**Purpose:** In the list view, staff should see at a glance whether an application has all required documents or is missing something.

**File:** `applications/admin.py`

Update the `display_docs` decorator on `ApplicationAdmin`:

```python
@display(
    description="Documents",
    label={
        "Complete": "success",
        "Missing": "danger",
        "Partial": "warning",
        "N/A": "info",
    },
)
def display_docs(self, instance):
    """Show document completeness based on purchase type."""
    docs = set(instance.documents.values_list("doc_type", flat=True))

    # Always required
    required = {"photo_id"}

    # Conditional on purchase type
    if instance.purchase_type == Application.PurchaseType.CASH:
        required.add("proof_of_funds")
    elif instance.purchase_type == Application.PurchaseType.LAND_CONTRACT:
        required.update(["pay_stubs", "bank_statement"])
    elif instance.purchase_type in [
        Application.PurchaseType.CONVENTIONAL,
        Application.PurchaseType.FHA_VA,
    ]:
        required.add("preapproval")

    if not required:
        return "N/A"

    have = docs & required
    if have == required:
        return "Complete"
    if have:
        return "Partial"
    return "Missing"
```

---

## Task 8: Add Staff Notes Field with Quick-Add

**Purpose:** Staff need a way to jot internal notes on an application without changing its status. Currently notes only exist on StatusLog entries.

**File:** `applications/models.py`

Add a `staff_notes` field to `Application`:

```python
# Add to the Application model, in the "Reference & Workflow" section:
staff_notes = models.TextField(
    blank=True,
    default="",
    help_text="Internal notes visible only to staff. Not shared with the applicant.",
)
```

Run migrations:
```bash
python manage.py makemigrations applications
python manage.py migrate
```

**File:** `applications/admin.py`

Add `staff_notes` to the "Reference" fieldset:

```python
fieldsets = (
    (
        "Reference",
        {
            "fields": ("reference_number", "status", "assigned_to", "staff_notes"),
        },
    ),
    # ... rest unchanged
)
```

---

## Task 9: Add Application Summary Card to Detail View

**Purpose:** When staff open an application, the most critical info should be visible without scrolling. Add a summary card at the top.

**File:** `templates/admin/applications/application/change_form.html`

Add this before `{{ block.super }}` in `after_field_sets`:

```html
{% block before_fieldsets %}
{{ block.super }}

{% if original %}
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 24px;">
  {# Applicant #}
  <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;">
    <p style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; margin: 0 0 6px;">Applicant</p>
    <p style="font-size: 16px; font-weight: 700; color: #111; margin: 0;">{{ original.full_name }}</p>
    <p style="font-size: 13px; color: #6b7280; margin: 4px 0 0;">{{ original.email }}</p>
    <p style="font-size: 13px; color: #6b7280; margin: 2px 0 0;">{{ original.phone }}</p>
  </div>

  {# Property #}
  <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;">
    <p style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; margin: 0 0 6px;">Property</p>
    <p style="font-size: 16px; font-weight: 700; color: #111; margin: 0;">{{ original.property_address }}</p>
    <p style="font-size: 13px; color: #6b7280; margin: 4px 0 0;">{{ original.get_program_type_display }}</p>
    {% if original.parcel_id %}
    <p style="font-size: 12px; font-family: monospace; color: #9ca3af; margin: 4px 0 0;">Parcel: {{ original.parcel_id }}</p>
    {% endif %}
  </div>

  {# Offer #}
  <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;">
    <p style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; margin: 0 0 6px;">Offer</p>
    <p style="font-size: 24px; font-weight: 800; color: #16a34a; margin: 0;">${{ original.offer_amount|floatformat:0 }}</p>
    <p style="font-size: 13px; color: #6b7280; margin: 4px 0 0;">{{ original.get_purchase_type_display }}</p>
    <p style="font-size: 13px; color: #6b7280; margin: 2px 0 0;">{{ original.get_intended_use_display }}</p>
  </div>
</div>
{% endif %}
{% endblock %}
```

---

## Task 10: Add Keyboard Shortcuts for Common Actions

**Purpose:** Staff reviewing applications all day benefit from keyboard shortcuts. "R" for review, "D" for request docs, "A" for approve.

**File:** `static/js/admin_shortcuts.js`

```js
/**
 * Keyboard shortcuts for the GCLBA admin.
 *
 * Only active on the Application change form (detail view).
 * Ctrl+Shift+R = Under Review
 * Ctrl+Shift+D = Request Documents
 * Ctrl+Shift+A = Approve
 * Ctrl+Shift+N = Deny
 */
(function () {
  "use strict";

  // Only run on application change form
  const statusSelect = document.querySelector('select[name="status"]');
  if (!statusSelect) return;

  const STATUS_MAP = {
    "R": "under_review",
    "D": "docs_requested",
    "A": "approved",
    "N": "denied",
  };

  document.addEventListener("keydown", function (e) {
    // Ctrl+Shift+<key>
    if (!e.ctrlKey || !e.shiftKey) return;

    const key = e.key.toUpperCase();
    if (!(key in STATUS_MAP)) return;

    e.preventDefault();
    statusSelect.value = STATUS_MAP[key];

    // Visual flash to confirm
    statusSelect.style.outline = "3px solid #16a34a";
    setTimeout(function () {
      statusSelect.style.outline = "";
    }, 600);
  });
})();
```

**File:** `templates/admin/applications/application/change_form.html`

Add at the bottom:

```html
{% block extrajs %}
{{ block.super }}
<script src="{% static 'js/admin_shortcuts.js' %}"></script>
{% endblock %}
```

---

## Completion Checklist

- [ ] `staff_dashboard` view created in `applications/views.py`
- [ ] `templates/admin/staff_dashboard.html` created with stat cards + recent submissions
- [ ] Dashboard wired into Unfold via `DASHBOARD_CALLBACK` in settings
- [ ] URL route added for `/admin/dashboard/`
- [ ] Status timeline in `templates/admin/applications/application/change_form.html`
- [ ] Batch actions added (Under Review, Request Docs, Assign to Me)
- [ ] Custom filters (AssignmentFilter, FreshnessFilter) added to list view
- [ ] Document completeness indicator updated in `display_docs`
- [ ] `staff_notes` field added to Application model + migration run
- [ ] Application summary card (applicant/property/offer) in detail view
- [ ] Keyboard shortcuts JS for status changes
- [ ] Visit `/admin/` and confirm dashboard renders
- [ ] Select applications and test batch actions
- [ ] Open an application and confirm timeline + summary card render
- [ ] Test keyboard shortcuts (Ctrl+Shift+R/D/A/N) on change form

## Why This Is Better Than the Old System

| Old Workflow (PDF/Email) | New Workflow (Portal Admin) |
|---|---|
| Open email, find PDF attachment, download, read | Click reference number, see summary card instantly |
| Check shared spreadsheet for status | Status badge visible in list view, filterable |
| Email colleague to ask "is anyone on this?" | "Assigned to" column, "Assign to me" batch action |
| Print PDF, write margin notes, refile | Staff notes field, persistent and searchable |
| Search inbox for "when did we last touch this?" | Status timeline shows full history with timestamps |
| Manually count "how many are pending?" | Dashboard stat cards, auto-updating |
| No way to see stale applications | Freshness filter surfaces anything stuck 14+ days |
| Forward email to colleague for assignment | Batch select, one click to assign |
