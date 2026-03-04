"""
Admin configuration for the GCLBA Application Portal.

Uses SmartBase Admin for a modern staff dashboard with colored status badges,
organized fieldsets, inline documents, and automatic status audit logging.
"""

import csv

from django import forms
from django.http import HttpResponse
from django.contrib import admin, messages
from django_smartbase_admin.admin.admin_base import SBAdminTableInline
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.db.models import Count, F, Value
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django_smartbase_admin.admin.admin_base import SBAdmin
from django_smartbase_admin.admin.site import sb_admin_site
from django_smartbase_admin.engine.field import SBAdminField

from .csv_import import import_properties_from_csv
from .models import Application, ApplicationDraft, Document, Property, StatusLog, User
from .status_notifications import requires_transition_note, send_buyer_status_email


# ── User forms (must point to custom User model, not auth.User) ──


class CustomUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


# ── User Admin (required for autocomplete_fields on assigned_to) ──


@admin.register(User, site=sb_admin_site)
class UserAdmin(SBAdmin, BaseUserAdmin):
    """Custom User admin for the GCLBA staff portal.

    SBAdmin must come first in the MRO so SmartBase's init_view_static()
    is available. BaseUserAdmin provides the user-specific fieldsets and forms.
    """

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm


# ── Property Admin ───────────────────────────────────────────────


@admin.register(Property, site=sb_admin_site)
class PropertyAdmin(SBAdmin):
    list_display = (
        "address",
        "parcel_id",
        "display_program",
        "display_status",
        "listing_price_display",
        "application_count",
        "imported_at",
    )
    # SmartBase AG Grid uses .values() — display methods get (obj_id, value, **kwargs),
    # NOT model instances. Use sb_* methods + sbadmin_list_display_data for extra fields.
    sbadmin_list_display = [
        "address",
        "parcel_id",
        SBAdminField(name="sb_program", title="Program", annotate=F("program_type")),
        SBAdminField(name="sb_status", title="Status", annotate=F("status")),
        SBAdminField(name="sb_price", title="Price", annotate=F("listing_price")),
        SBAdminField(
            name="sb_app_count",
            title="Apps",
            annotate=Count("applications"),
        ),
        "imported_at",
    ]
    list_filter = ("program_type", "status", "csv_batch")
    search_fields = ("address", "parcel_id")
    readonly_fields = ("address_normalized", "imported_at")
    list_per_page = 50
    ordering = ("address",)
    actions = ("import_csv_action", "mark_withdrawn", "mark_available")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "address",
                    "address_normalized",
                    "parcel_id",
                    "program_type",
                    "listing_price",
                    "status",
                    "csv_batch",
                    "imported_at",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        from django.db.models import Count

        return (
            super()
            .get_queryset(request)
            .annotate(_application_count=Count("applications"))
        )

    # ── SmartBase list view methods (receive obj_id, value, **kwargs) ──

    PROGRAM_PALETTE = {
        Application.ProgramType.FEATURED_HOMES: ("#dcfce7", "#166534"),
        Application.ProgramType.READY_FOR_REHAB: ("#fef3c7", "#92400e"),
        Application.ProgramType.VIP_SPOTLIGHT: ("#dbeafe", "#1e40af"),
        Application.ProgramType.VACANT_LOT: ("#dbeafe", "#1e40af"),
    }

    PROPERTY_STATUS_PALETTE = {
        Property.Status.AVAILABLE: ("#dcfce7", "#166534"),
        Property.Status.UNDER_OFFER: ("#fef3c7", "#92400e"),
        Property.Status.SOLD: ("#dbeafe", "#1e40af"),
        Property.Status.WITHDRAWN: ("#fee2e2", "#991b1b"),
    }

    def sb_program(self, obj_id, value, **kwargs):
        """SmartBase list view: program badge. `value` = program_type string."""
        bg, fg = self.PROGRAM_PALETTE.get(value, ("#e5e7eb", "#374151"))
        label = dict(Application.ProgramType.choices).get(value, value or "—")
        return format_html(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:{};color:{}'>{}</span>",
            bg, fg, label,
        )

    def sb_status(self, obj_id, value, **kwargs):
        """SmartBase list view: status badge. `value` = status string."""
        bg, fg = self.PROPERTY_STATUS_PALETTE.get(value, ("#e5e7eb", "#374151"))
        label = dict(Property.Status.choices).get(value, value or "—")
        return format_html(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:{};color:{}'>{}</span>",
            bg, fg, label,
        )

    def sb_price(self, obj_id, value, **kwargs):
        """SmartBase list view: formatted price. `value` = listing_price Decimal."""
        if value is None:
            return "N/A"
        return f"${value:,.2f}"

    def sb_app_count(self, obj_id, value, **kwargs):
        """SmartBase list view: application count. `value` = Count annotation."""
        return value or 0

    # ── Dual-compatible display methods (instance OR obj_id+value) ──

    @admin.display(description="Program", ordering="program_type")
    def display_program(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Property):
            program = obj_or_id.program_type
            label = obj_or_id.get_program_type_display()
        else:
            program = value
            label = dict(Application.ProgramType.choices).get(value, value or "—")
        bg, fg = self.PROGRAM_PALETTE.get(program, ("#e5e7eb", "#374151"))
        return format_html(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:{};color:{}'>{}</span>",
            bg, fg, label,
        )

    @admin.display(description="Status", ordering="status")
    def display_status(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Property):
            status = obj_or_id.status
            label = obj_or_id.get_status_display()
        else:
            status = value
            label = dict(Property.Status.choices).get(value, value or "—")
        bg, fg = self.PROPERTY_STATUS_PALETTE.get(status, ("#e5e7eb", "#374151"))
        return format_html(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:{};color:{}'>{}</span>",
            bg, fg, label,
        )

    @admin.display(description="Price", ordering="listing_price")
    def listing_price_display(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Property):
            price = obj_or_id.listing_price
        else:
            price = value
        if price is None:
            return "N/A"
        return f"${price:,.2f}"

    @admin.display(description="Apps")
    def application_count(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Property):
            return obj_or_id._application_count
        return value or 0

    @admin.action(description="Import properties from CSV")
    def import_csv_action(self, request, queryset):
        """Placeholder - CSV import is handled via the changelist toolbar."""
        self.message_user(
            request,
            "Use the management command: python manage.py import_properties <file.csv>",
            level=messages.INFO,
        )

    @admin.action(description="Mark selected as Withdrawn")
    def mark_withdrawn(self, request, queryset):
        updated = queryset.exclude(status=Property.Status.WITHDRAWN).update(
            status=Property.Status.WITHDRAWN
        )
        self.message_user(request, f"Marked {updated} properties as withdrawn.")

    @admin.action(description="Mark selected as Available")
    def mark_available(self, request, queryset):
        updated = queryset.exclude(status=Property.Status.AVAILABLE).update(
            status=Property.Status.AVAILABLE
        )
        self.message_user(request, f"Marked {updated} properties as available.")


# ── Inlines ──────────────────────────────────────────────────────


class DocumentInline(SBAdminTableInline):
    model = Document
    extra = 0
    fields = ("doc_type", "file", "view_file", "original_filename", "uploaded_at")
    readonly_fields = ("view_file", "uploaded_at")

    @admin.display(description="View", ordering="uploaded_at")
    def view_file(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Document):
            if not obj_or_id.pk or not obj_or_id.file:
                return "N/A"
            pk = obj_or_id.pk
        else:
            # SmartBase path — obj_or_id is the PK
            pk = obj_or_id
        url = reverse("applications:document_view", args=[pk])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Open</a>',
            url,
        )


class StatusLogInline(SBAdminTableInline):
    model = StatusLog
    extra = 0
    fields = ("from_status", "to_status", "changed_by", "notes", "changed_at")
    readonly_fields = ("from_status", "to_status", "changed_by", "changed_at")
    classes = ("collapse",)


class DocsStateFilter(admin.SimpleListFilter):
    """Filter applications by whether required documents are complete."""

    title = "documents"
    parameter_name = "docs_state"

    def lookups(self, request, model_admin):
        return (
            ("complete", "Complete"),
            ("missing", "Missing"),
        )

    def queryset(self, request, queryset):
        choice = self.value()
        if choice not in {"complete", "missing"}:
            return queryset

        target_complete = choice == "complete"
        matching_ids = [
            app.pk
            for app in queryset.prefetch_related("documents")
            if app.docs_complete == target_complete
        ]
        return queryset.filter(pk__in=matching_ids)


class AssignmentFilter(admin.SimpleListFilter):
    """Quick filter: my apps, unassigned, or assigned to others."""

    title = "assignment"
    parameter_name = "assignment"

    def lookups(self, request, model_admin):
        return [
            ("mine", "My reviews"),
            ("unassigned", "Needs reviewer"),
            ("others", "Other reviewer"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "mine":
            return queryset.filter(assigned_to=request.user)
        if self.value() == "unassigned":
            return queryset.filter(assigned_to__isnull=True)
        if self.value() == "others":
            return queryset.filter(assigned_to__isnull=False).exclude(
                assigned_to=request.user
            )
        return queryset


class FreshnessFilter(admin.SimpleListFilter):
    """Quick filter: submitted today, this week, or stale (14+ days in review)."""

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


class ApplicationAdminForm(forms.ModelForm):
    """Admin form with transition-note requirements for buyer-facing updates."""

    class Meta:
        model = Application
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        new_status = cleaned.get("status")

        # Instance with no PK means a brand-new object creation in admin.
        if not self.instance.pk or not new_status:
            return cleaned

        old_status = self.instance.status
        if old_status == new_status:
            return cleaned

        # Enforce allowed state transitions
        allowed = Application.ALLOWED_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            old_label = dict(Application.Status.choices).get(old_status, old_status)
            new_label = dict(Application.Status.choices).get(new_status, new_status)
            if allowed:
                valid_labels = ", ".join(
                    dict(Application.Status.choices).get(s, s) for s in sorted(allowed)
                )
                self.add_error(
                    "status",
                    f"Cannot move from {old_label} to {new_label}. "
                    f"Valid transitions: {valid_labels}.",
                )
            else:
                self.add_error(
                    "status",
                    f"{old_label} is a terminal status and cannot be changed.",
                )
            return cleaned

        if requires_transition_note(new_status):
            note = (cleaned.get("staff_notes") or "").strip()
            if not note:
                self.add_error(
                    "staff_notes",
                    "A transition note is required when setting status to "
                    f"{dict(Application.Status.choices).get(new_status, new_status)}.",
                )

        return cleaned


# ── Application Admin ────────────────────────────────────────────


@admin.register(Application, site=sb_admin_site)
class ApplicationAdmin(SBAdmin):
    change_form_template = "admin/applications/application/change_form.html"

    COMMON_FIELDSET_TITLES = {
        "Review Snapshot",
        "Applicant Identity",
        "Property & Program",
        "Eligibility",
        "Acknowledgments",
        "Timestamps",
    }

    PROGRAM_FIELDSET_TITLES = {
        Application.ProgramType.FEATURED_HOMES: {
            "Offer Details",
            "Intended Use & Renovation Narrative",
        },
        Application.ProgramType.READY_FOR_REHAB: {
            "Offer Details",
            "Intended Use & Renovation Narrative",
            "R4R: Renovation Line Items - Interior",
            "R4R: Renovation Line Items - Exterior",
            "R4R: Prior GCLBA Purchase",
        },
        Application.ProgramType.VIP_SPOTLIGHT: {"VIP Proposal"},
        Application.ProgramType.VACANT_LOT: set(),
    }

    DOC_SHORT_LABELS = {
        Document.DocType.PHOTO_ID: "ID",
        Document.DocType.PROOF_OF_FUNDS: "Funds",
        Document.DocType.PROOF_OF_INCOME: "Income",
        Document.DocType.PROOF_OF_DOWN_PAYMENT: "Down",
        Document.DocType.RENO_FUNDING_PROOF: "Reno",
        Document.DocType.PRIOR_INVESTMENT_PROOF: "Prior",
        Document.DocType.VIP_PREAPPROVAL: "PreApp",
        Document.DocType.VIP_PORTFOLIO_PHOTO: "Portfolio",
        Document.DocType.VIP_SUPPORT_LETTER: "Support",
    }

    list_display = (
        "reference_number",
        "display_full_name",
        "property_address",
        "display_program",
        "display_purchase_type",
        "display_offer",
        "display_status",
        "display_docs",
        "quick_docs",
        "display_assignee",
        "submitted_age",
    )

    # SmartBase AG Grid uses .values() (flat dicts, not instances).
    # sb_* methods accept (self, obj_id, value, **kwargs).
    # Extra fields for kwargs come from sbadmin_list_display_data.
    sbadmin_list_display_data = [
        "first_name",
        "last_name",
        "program_type",
        "purchase_type",
        "offer_amount",
        "status",
        "assigned_to__first_name",
        "assigned_to__last_name",
        "assigned_to__username",
    ]

    sbadmin_list_display = [
        "reference_number",
        SBAdminField(
            name="sb_full_name",
            title="Name",
            annotate=Concat(
                F("first_name"), Value(" "), F("last_name"),
            ),
        ),
        "property_address",
        SBAdminField(name="sb_program", title="Program", annotate=F("program_type")),
        SBAdminField(
            name="sb_purchase_type",
            title="Purchase Type",
            annotate=F("purchase_type"),
        ),
        SBAdminField(name="sb_offer", title="Offer", annotate=F("offer_amount")),
        SBAdminField(name="sb_status", title="Status", annotate=F("status")),
        SBAdminField(name="sb_docs", title="Docs", annotate=Count("documents")),
        SBAdminField(
            name="sb_reviewer",
            title="Reviewer",
            annotate=F("assigned_to_id"),
        ),
        SBAdminField(name="sb_age", title="Age", annotate=F("submitted_at")),
    ]
    list_filter = (
        AssignmentFilter,
        FreshnessFilter,
        "status",
        "program_type",
        "purchase_type",
        DocsStateFilter,
        "submitted_at",
    )
    list_display_links = ("reference_number",)
    date_hierarchy = "submitted_at"
    ordering = ("-submitted_at",)
    list_per_page = 50
    search_fields = (
        "reference_number",
        "first_name",
        "last_name",
        "email",
        "phone",
        "property_address",
        "parcel_id",
    )
    autocomplete_fields = ("assigned_to",)
    readonly_fields = (
        "reference_number",
        "display_docs",
        "quick_docs",
        "closing_fee_display",
        "submitted_age",
        "created_at",
        "updated_at",
        "submitted_at",
    )
    inlines = [DocumentInline, StatusLogInline]
    actions = (
        "mark_under_review",
        "mark_needs_more_info",
        "mark_approved",
        "mark_declined",
        "assign_to_me",
        "clear_assignee",
        "export_csv",
    )

    fieldsets = (
        (
            "Review Snapshot",
            {
                "fields": (
                    ("reference_number", "status"),
                    ("assigned_to", "display_docs"),
                    "quick_docs",
                    ("submitted_age", "closing_fee_display"),
                    "staff_notes",
                ),
            },
        ),
        (
            "Applicant Identity",
            {
                "fields": (
                    ("first_name", "last_name"),
                    "email",
                    "phone",
                    "preferred_contact",
                    "mailing_address",
                    ("city", "state", "zip_code"),
                    ("purchasing_entity_name", "contact_name_different"),
                ),
            },
        ),
        (
            "Property & Program",
            {
                "fields": (
                    "property_ref",
                    "property_address",
                    "parcel_id",
                    "program_type",
                    "attended_open_house",
                    "open_house_date",
                ),
            },
        ),
        (
            "Eligibility",
            {
                "fields": ("has_delinquent_taxes", "has_tax_foreclosure"),
                "description": "If either is Yes, the applicant should have been disqualified at Step 3.",
            },
        ),
        (
            "Offer Details",
            {
                "fields": (
                    "offer_amount",
                    "purchase_type",
                    "down_payment_amount",
                    "is_self_employed",
                ),
            },
        ),
        (
            "Intended Use & Renovation Narrative",
            {
                "fields": (
                    "intended_use",
                    "first_home_or_moving",
                    "renovation_description",
                    "renovation_who",
                    "renovation_when",
                    "renovation_funding",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "R4R: Renovation Line Items - Interior",
            {
                "fields": (
                    "reno_clean_out",
                    "reno_demolition_disposal",
                    "reno_hvac",
                    "reno_water_heater",
                    "reno_plumbing",
                    "reno_electrical",
                    "reno_kitchen_cabinets",
                    "reno_kitchen_appliances",
                    "reno_bathroom_repairs",
                    "reno_flooring",
                    "reno_doors_int",
                    "reno_insulation",
                    "reno_drywall_plaster",
                    "reno_paint_wallpaper",
                    "reno_lighting_int",
                    "reno_interior_subtotal",
                ),
                "classes": ("collapse",),
                "description": "Only applicable for Ready for Rehab applications.",
            },
        ),
        (
            "R4R: Renovation Line Items - Exterior",
            {
                "fields": (
                    "reno_cleanup_landscaping",
                    "reno_roof",
                    "reno_foundation",
                    "reno_doors_ext",
                    "reno_windows",
                    "reno_siding",
                    "reno_masonry",
                    "reno_porch_decking",
                    "reno_lighting_ext",
                    "reno_garage",
                    "reno_exterior_subtotal",
                    "reno_total",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "R4R: Prior GCLBA Purchase",
            {
                "fields": ("has_prior_gclba_purchase",),
                "classes": ("collapse",),
            },
        ),
        (
            "Homebuyer Education (Land Contract Only)",
            {
                "fields": (
                    "homebuyer_ed_completed",
                    "homebuyer_ed_agency",
                    "homebuyer_ed_other",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "VIP Proposal",
            {
                "fields": (
                    "vip_q1_who_and_why",
                    "vip_q2_prior_purchases",
                    "vip_q2_prior_detail",
                    "vip_q3_renovation_costs_timeline",
                    "vip_q4_financing",
                    "vip_q5_has_experience",
                    "vip_q5_experience_detail",
                    "vip_q6_completion_plan",
                    "vip_q6_completion_detail",
                    "vip_q7_contractor_info",
                    "vip_q8_additional_info",
                ),
                "classes": ("collapse",),
                "description": "Only applicable for VIP Spotlight applications.",
            },
        ),
        (
            "Acknowledgments",
            {
                "fields": (
                    "ack_sold_as_is",
                    "ack_quit_claim_deed",
                    "ack_no_title_insurance",
                    "ack_highest_not_guaranteed",
                    "ack_info_accurate",
                    "ack_tax_capture",
                    "ack_reconveyance_deed",
                    "ack_no_transfer",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("submitted_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        """Applications are created only through the buyer form, not by staff."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete applications — prevents accidental loss."""
        return request.user.is_superuser

    def get_fieldsets(self, request, obj=None):
        """Hide irrelevant field groups for the selected program."""
        if obj is None:
            return self.fieldsets

        allowed = set(self.COMMON_FIELDSET_TITLES)
        allowed |= self.PROGRAM_FIELDSET_TITLES.get(obj.program_type, set())
        if (
            obj.program_type == Application.ProgramType.FEATURED_HOMES
            and obj.purchase_type == Application.PurchaseType.LAND_CONTRACT
        ):
            allowed.add("Homebuyer Education (Land Contract Only)")

        return tuple(fieldset for fieldset in self.fieldsets if fieldset[0] in allowed)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("assigned_to")
            .prefetch_related("documents")
        )

    # ── SmartBase AG Grid list view methods ──────────────────────
    # These accept (self, obj_id, value, **kwargs) where value comes from
    # annotate=F(...) and kwargs come from sbadmin_list_display_data.

    APP_STATUS_PALETTE = {
        Application.Status.RECEIVED: ("#dbeafe", "#1e40af"),
        Application.Status.UNDER_REVIEW: ("#fef3c7", "#92400e"),
        Application.Status.NEEDS_MORE_INFO: ("#ffedd5", "#9a3412"),
        Application.Status.APPROVED: ("#dcfce7", "#166534"),
        Application.Status.DECLINED: ("#fee2e2", "#991b1b"),
    }

    APP_PROGRAM_PALETTE = {
        Application.ProgramType.FEATURED_HOMES: ("#dcfce7", "#166534"),
        Application.ProgramType.READY_FOR_REHAB: ("#fef3c7", "#92400e"),
        Application.ProgramType.VIP_SPOTLIGHT: ("#dbeafe", "#1e40af"),
        Application.ProgramType.VACANT_LOT: ("#dbeafe", "#1e40af"),
    }

    def sb_full_name(self, obj_id, value, **kwargs):
        """SmartBase list: full name. `value` = Concat(first, ' ', last)."""
        return value or "—"

    def sb_program(self, obj_id, value, **kwargs):
        """SmartBase list: program badge. `value` = program_type string."""
        bg, fg = self.APP_PROGRAM_PALETTE.get(value, ("#e5e7eb", "#374151"))
        label = dict(Application.ProgramType.choices).get(value, value or "—")
        return format_html(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:{};color:{}'>{}</span>",
            bg, fg, label,
        )

    def sb_purchase_type(self, obj_id, value, **kwargs):
        """SmartBase list: purchase type. `value` = purchase_type string."""
        program = kwargs.get("program_type")
        if program == Application.ProgramType.VIP_SPOTLIGHT:
            return "Proposal"
        return dict(Application.PurchaseType.choices).get(value, value or "—")

    def sb_offer(self, obj_id, value, **kwargs):
        """SmartBase list: offer amount. `value` = offer_amount Decimal."""
        program = kwargs.get("program_type")
        if program == Application.ProgramType.VIP_SPOTLIGHT:
            return "See Proposal"
        if value is None:
            return "N/A"
        return f"${value:,.2f}"

    def sb_status(self, obj_id, value, **kwargs):
        """SmartBase list: status badge. `value` = status string."""
        bg, fg = self.APP_STATUS_PALETTE.get(value, ("#e5e7eb", "#374151"))
        label = dict(Application.Status.choices).get(value, value or "—")
        return format_html(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:{};color:{}'>{}</span>",
            bg, fg, label,
        )

    def sb_docs(self, obj_id, value, **kwargs):
        """SmartBase list: doc count badge. `value` = Count(documents)."""
        count = value or 0
        if count > 0:
            return format_html(
                "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
                "border-radius:999px;font-size:12px;font-weight:600;"
                "background:#dcfce7;color:#166534'>{} doc{}</span>",
                count, "s" if count != 1 else "",
            )
        return mark_safe(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:#fee2e2;color:#991b1b'>None</span>"
        )

    def sb_reviewer(self, obj_id, value, **kwargs):
        """SmartBase list: reviewer name or Claim button. `value` = assigned_to_id."""
        if not value:
            return format_html(
                '<span id="claim-{pk}">'
                '<button type="button" '
                'hx-post="/admin/api/assign/{pk}/" '
                'hx-target="#claim-{pk}" '
                'hx-swap="innerHTML" '
                'onclick="event.stopPropagation()" '
                'style="display:inline-flex;align-items:center;padding:2px 10px;'
                'border-radius:999px;font-size:12px;font-weight:600;cursor:pointer;'
                'background:#dbeafe;color:#1e40af;border:1px solid #93c5fd">'
                'Claim</button></span>',
                pk=obj_id,
            )
        first = kwargs.get("assigned_to__first_name", "")
        last = kwargs.get("assigned_to__last_name", "")
        full = f"{first} {last}".strip()
        return full or kwargs.get("assigned_to__username", "Staff")

    def sb_age(self, obj_id, value, **kwargs):
        """SmartBase list: age pill. `value` = submitted_at datetime."""
        if not value:
            return "—"
        days_open = (timezone.now() - value).days
        if days_open == 0:
            label = "Today"
        elif days_open == 1:
            label = "1 day"
        else:
            label = f"{days_open} days"

        status = kwargs.get("status")
        open_statuses = (
            Application.Status.RECEIVED,
            Application.Status.UNDER_REVIEW,
            Application.Status.NEEDS_MORE_INFO,
        )
        if status not in open_statuses:
            return label

        if days_open >= 14:
            bg, color = "#fee2e2", "#991b1b"
        elif days_open >= 7:
            bg, color = "#fef3c7", "#92400e"
        else:
            bg, color = "#dcfce7", "#166534"

        return format_html(
            '<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
            'font-size:12px;font-weight:600;background:{bg};color:{color}">{label}</span>',
            bg=bg, color=color, label=label,
        )

    # ── Dual-compatible display methods ──────────────────────────
    # These handle BOTH calling conventions:
    #   Django detail/change view: (self, instance)    — instance is a model object
    #   SmartBase AG Grid list:    (self, obj_id, value, **kwargs) — obj_id is PK int
    # The isinstance() check detects which path we're on.

    @admin.display(description="Name", ordering="last_name")
    def display_full_name(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            return obj_or_id.full_name
        # SmartBase path — use kwargs from sbadmin_list_display_data
        first = kwargs.get("first_name", "")
        last = kwargs.get("last_name", "")
        return f"{first} {last}".strip() or value or "—"

    @admin.display(description="Status", ordering="status")
    def display_status(self, obj_or_id, value=None, **kwargs):
        palette = {
            Application.Status.RECEIVED: ("#dbeafe", "#1e40af"),
            Application.Status.UNDER_REVIEW: ("#fef3c7", "#92400e"),
            Application.Status.NEEDS_MORE_INFO: ("#ffedd5", "#9a3412"),
            Application.Status.APPROVED: ("#dcfce7", "#166534"),
            Application.Status.DECLINED: ("#fee2e2", "#991b1b"),
        }
        if isinstance(obj_or_id, Application):
            status = obj_or_id.status
            label = obj_or_id.get_status_display()
        else:
            status = value
            label = dict(Application.Status.choices).get(value, value or "—")
        bg, fg = palette.get(status, ("#e5e7eb", "#374151"))
        return format_html(
            (
                "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
                "border-radius:999px;font-size:12px;font-weight:600;"
                "background:{};color:{}'>{}</span>"
            ),
            bg,
            fg,
            label,
        )

    @admin.display(description="Program", ordering="program_type")
    def display_program(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            return obj_or_id.get_program_type_display()
        return dict(Application.ProgramType.choices).get(value, value or "—")

    @admin.display(description="Purchase Type", ordering="purchase_type")
    def display_purchase_type(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            if obj_or_id.program_type == Application.ProgramType.VIP_SPOTLIGHT:
                return "Proposal"
            return obj_or_id.get_purchase_type_display()
        # SmartBase path
        program = kwargs.get("program_type")
        if program == Application.ProgramType.VIP_SPOTLIGHT:
            return "Proposal"
        return dict(Application.PurchaseType.choices).get(value, value or "—")

    @admin.display(description="Offer", ordering="offer_amount")
    def display_offer(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            if obj_or_id.program_type == Application.ProgramType.VIP_SPOTLIGHT:
                return "See Proposal"
            if obj_or_id.offer_amount is None:
                return "N/A"
            return f"${obj_or_id.offer_amount:,.2f}"
        # SmartBase path
        program = kwargs.get("program_type")
        if program == Application.ProgramType.VIP_SPOTLIGHT:
            return "See Proposal"
        if value is None:
            return "N/A"
        return f"${value:,.2f}"

    @admin.display(description="Docs", ordering="submitted_at")
    def display_docs(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            is_complete = obj_or_id.docs_complete
        else:
            # SmartBase path — no reliable way to check docs_complete, show "—"
            return "—"
        if is_complete:
            return mark_safe(
                "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
                "border-radius:999px;font-size:12px;font-weight:600;"
                "background:#dcfce7;color:#166534'>Complete</span>"
            )
        return mark_safe(
            "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
            "border-radius:999px;font-size:12px;font-weight:600;"
            "background:#fee2e2;color:#991b1b'>Incomplete</span>"
        )

    @admin.display(description="Quick Docs", ordering="submitted_at")
    def quick_docs(self, obj_or_id, value=None, **kwargs):
        if not isinstance(obj_or_id, Application):
            # SmartBase path — needs full instance for documents queryset, skip
            return "—"
        instance = obj_or_id
        docs = list(instance.documents.all())
        if not docs:
            return "N/A"

        links_html = format_html_join(
            " ",
            (
                "<a href='{}' target='_blank' rel='noopener' title='{}'"
                " onclick='event.stopPropagation()' style="
                "'display:inline-flex;align-items:center;padding:2px 6px;border-radius:999px;"
                "background:#eef2ff;color:#1e3a8a;font-size:11px;font-weight:600;text-decoration:none'>"
                "{}</a>"
            ),
            (
                (
                    reverse("applications:document_view", args=[doc.pk]),
                    doc.get_doc_type_display(),
                    self.DOC_SHORT_LABELS.get(doc.doc_type, "Doc"),
                )
                for doc in docs[:2]
            ),
        )
        wrap = "<div style='display:flex;flex-wrap:wrap;gap:4px;max-width:180px'>{}</div>"
        if len(docs) > 2:
            return format_html(
                wrap,
                format_html(
                    "{} <span style='color:#6b7280;font-size:11px'>+{} more</span>",
                    links_html,
                    len(docs) - 2,
                ),
            )
        return format_html(wrap, links_html)

    @admin.display(description="Reviewer", ordering="assigned_to")
    def display_assignee(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            instance = obj_or_id
            if not instance.assigned_to:
                return format_html(
                    '<span id="claim-{pk}">'
                    '<button type="button" '
                    'hx-post="/admin/api/assign/{pk}/" '
                    'hx-target="#claim-{pk}" '
                    'hx-swap="innerHTML" '
                    'onclick="event.stopPropagation()" '
                    'style="display:inline-flex;align-items:center;padding:2px 10px;'
                    'border-radius:999px;font-size:12px;font-weight:600;cursor:pointer;'
                    'background:#dbeafe;color:#1e40af;border:1px solid #93c5fd">'
                    'Claim</button></span>',
                    pk=instance.pk,
                )
            return instance.assigned_to.get_full_name() or instance.assigned_to.get_username()
        # SmartBase path — use kwargs from sbadmin_list_display_data
        assigned_id = kwargs.get("assigned_to_id") or value
        if not assigned_id:
            return format_html(
                '<span id="claim-{pk}">'
                '<button type="button" '
                'hx-post="/admin/api/assign/{pk}/" '
                'hx-target="#claim-{pk}" '
                'hx-swap="innerHTML" '
                'onclick="event.stopPropagation()" '
                'style="display:inline-flex;align-items:center;padding:2px 10px;'
                'border-radius:999px;font-size:12px;font-weight:600;cursor:pointer;'
                'background:#dbeafe;color:#1e40af;border:1px solid #93c5fd">'
                'Claim</button></span>',
                pk=obj_or_id,
            )
        first = kwargs.get("assigned_to__first_name", "")
        last = kwargs.get("assigned_to__last_name", "")
        full = f"{first} {last}".strip()
        return full or kwargs.get("assigned_to__username", "Staff")

    @admin.display(description="Age", ordering="submitted_at")
    def submitted_age(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            submitted_at = obj_or_id.submitted_at
            status = obj_or_id.status
        else:
            submitted_at = value
            status = kwargs.get("status")

        if not submitted_at:
            return "—"
        days_open = (timezone.now() - submitted_at).days
        if days_open == 0:
            label = "Today"
        elif days_open == 1:
            label = "1 day"
        else:
            label = f"{days_open} days"

        # Only color-code open statuses (received, under review, needs more info)
        open_statuses = (
            Application.Status.RECEIVED,
            Application.Status.UNDER_REVIEW,
            Application.Status.NEEDS_MORE_INFO,
        )
        if status not in open_statuses:
            return label

        # Green < 7 days, amber 7-13, red 14+
        if days_open >= 14:
            bg, color = "#fee2e2", "#991b1b"
        elif days_open >= 7:
            bg, color = "#fef3c7", "#92400e"
        else:
            bg, color = "#dcfce7", "#166534"

        return format_html(
            '<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
            'font-size:12px;font-weight:600;background:{bg};color:{color}">{label}</span>',
            bg=bg,
            color=color,
            label=label,
        )

    @admin.display(description="Closing Fee", ordering="purchase_type")
    def closing_fee_display(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, Application):
            program = obj_or_id.program_type
            purchase = obj_or_id.purchase_type
        else:
            program = kwargs.get("program_type", value)
            purchase = kwargs.get("purchase_type")
        if program == Application.ProgramType.FEATURED_HOMES:
            if purchase == Application.PurchaseType.LAND_CONTRACT:
                return "$125"
            return "$75"
        if program == Application.ProgramType.READY_FOR_REHAB:
            return "$75"
        if program == Application.ProgramType.VIP_SPOTLIGHT:
            return "Per Purchase & Development Agreement"
        return "TBD"

    def _bulk_set_status(self, request, queryset, new_status):
        # Don't use .only() here — the base queryset from get_queryset() has
        # .select_related("assigned_to"), and .only() without that field causes
        # FieldError in Django 6.0. Bulk actions operate on a small selection
        # so the overhead is negligible.
        apps = list(queryset)
        changed = [app for app in apps if app.status != new_status]
        if not changed:
            self.message_user(request, "No status changes were needed.")
            return

        skipped_missing_note = []
        skipped_bad_transition = []
        eligible = []
        for app in changed:
            # Enforce allowed state transitions
            allowed = Application.ALLOWED_TRANSITIONS.get(app.status, set())
            if new_status not in allowed:
                skipped_bad_transition.append(app.reference_number)
                continue
            note = (app.staff_notes or "").strip()
            if requires_transition_note(new_status) and not note:
                skipped_missing_note.append(app.reference_number)
                continue
            eligible.append(app)

        if not eligible:
            parts = []
            if skipped_bad_transition:
                parts.append(
                    f"{len(skipped_bad_transition)} skipped (invalid transition)"
                )
            if skipped_missing_note:
                parts.append(
                    f"{len(skipped_missing_note)} skipped (missing staff note)"
                )
            self.message_user(
                request,
                f"No updates applied. {'; '.join(parts)}.",
                level=messages.WARNING,
            )
            return

        ids = [app.id for app in eligible]
        old_status_map = {app.id: app.status for app in eligible}
        note_by_id = {app.id: (app.staff_notes or "").strip() for app in eligible}
        updated_at = timezone.now()

        Application.objects.filter(id__in=ids).update(status=new_status, updated_at=updated_at)
        StatusLog.objects.bulk_create(
            [
                StatusLog(
                    application_id=app_id,
                    from_status=old_status_map[app_id],
                    to_status=new_status,
                    changed_by=request.user,
                    notes=note_by_id[app_id],
                )
                for app_id in ids
            ]
        )

        email_failures = 0
        for app in eligible:
            app.status = new_status
            outcome = send_buyer_status_email(
                application=app,
                old_status=old_status_map[app.id],
                note=note_by_id[app.id],
            )
            if outcome == "failed":
                email_failures += 1
                log = StatusLog.objects.filter(
                    application_id=app.id,
                    to_status=new_status,
                ).order_by("-changed_at").first()
                if log:
                    log.notes = (
                        (log.notes or "")
                        + "\n[SYSTEM] Buyer notification email failed. Manual follow-up needed."
                    ).strip()
                    log.save(update_fields=["notes"])

        msg = f"Updated {len(ids)} application(s)."
        if skipped_bad_transition:
            msg += f" Skipped {len(skipped_bad_transition)} (invalid transition)."
        if skipped_missing_note:
            msg += f" Skipped {len(skipped_missing_note)} without required notes."
        if email_failures:
            msg += f" {email_failures} buyer status email(s) failed."

        has_issues = skipped_bad_transition or skipped_missing_note or email_failures
        level = messages.WARNING if has_issues else messages.SUCCESS
        self.message_user(request, msg, level=level)

    @admin.action(description="Set status to Under Review")
    def mark_under_review(self, request, queryset):
        self._bulk_set_status(request, queryset, Application.Status.UNDER_REVIEW)

    @admin.action(description="Set status to Needs More Info")
    def mark_needs_more_info(self, request, queryset):
        self._bulk_set_status(request, queryset, Application.Status.NEEDS_MORE_INFO)

    @admin.action(description="Set status to Approved")
    def mark_approved(self, request, queryset):
        self._bulk_set_status(request, queryset, Application.Status.APPROVED)

    @admin.action(description="Set status to Declined")
    def mark_declined(self, request, queryset):
        self._bulk_set_status(request, queryset, Application.Status.DECLINED)

    @admin.action(description="Set me as reviewer")
    def assign_to_me(self, request, queryset):
        try:
            eligible = queryset.exclude(assigned_to=request.user)
            updated = 0
            reviewer_name = request.user.get_full_name() or request.user.get_username()
            for app in eligible:
                old_assignee = app.assigned_to
                app.assigned_to = request.user
                app.save(update_fields=["assigned_to", "updated_at"])
                StatusLog.objects.create(
                    application=app,
                    from_status=app.status,
                    to_status=app.status,
                    changed_by=request.user,
                    notes=(
                        f"Reviewer changed to {reviewer_name}"
                        + (
                            f" (was: {old_assignee.get_full_name() or old_assignee.get_username()})"
                            if old_assignee
                            else " (was: unassigned)"
                        )
                    ),
                )
                updated += 1
            self.message_user(request, f"You are now reviewer for {updated} application(s).")
        except Exception as e:
            self.message_user(
                request,
                f"Could not assign reviewer: {e}",
                level=messages.ERROR,
            )

    @admin.action(description="Remove reviewer")
    @admin.action(description="Export selected as CSV")
    def export_csv(self, request, queryset):
        """Export selected applications to a downloadable CSV file."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="applications_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Reference #",
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Property Address",
            "Parcel ID",
            "Program",
            "Purchase Type",
            "Offer Amount",
            "Status",
            "Reviewer",
            "Submitted",
            "Last Updated",
        ])

        for app in queryset.select_related("assigned_to").order_by("-submitted_at"):
            reviewer = ""
            if app.assigned_to:
                reviewer = app.assigned_to.get_full_name() or app.assigned_to.get_username()
            writer.writerow([
                app.reference_number,
                app.first_name,
                app.last_name,
                app.email,
                app.phone,
                app.property_address,
                app.parcel_id,
                app.get_program_type_display(),
                app.get_purchase_type_display(),
                f"${app.offer_amount:,.2f}" if app.offer_amount else "",
                app.get_status_display(),
                reviewer,
                app.submitted_at.strftime("%Y-%m-%d %I:%M %p") if app.submitted_at else "",
                app.updated_at.strftime("%Y-%m-%d %I:%M %p") if app.updated_at else "",
            ])

        return response

    def clear_assignee(self, request, queryset):
        eligible = queryset.exclude(assigned_to=None)
        updated = 0
        for app in eligible:
            old_assignee = app.assigned_to
            old_name = old_assignee.get_full_name() or old_assignee.get_username()
            app.assigned_to = None
            app.save(update_fields=["assigned_to", "updated_at"])
            StatusLog.objects.create(
                application=app,
                from_status=app.status,
                to_status=app.status,
                changed_by=request.user,
                notes=f"Reviewer removed (was: {old_name})",
            )
            updated += 1
        self.message_user(request, f"Removed reviewer from {updated} application(s).")

    def save_model(self, request, obj, form, change):
        """Auto-create StatusLog when status changes."""
        if change:
            old_status = form.initial.get("status", "")
            new_status = obj.status
            if old_status != new_status:
                super().save_model(request, obj, form, change)
                note = (obj.staff_notes or "").strip()
                StatusLog.objects.create(
                    application=obj,
                    from_status=old_status,
                    to_status=new_status,
                    changed_by=request.user,
                    notes=note,
                )
                outcome = send_buyer_status_email(
                    application=obj,
                    old_status=old_status,
                    note=note,
                )
                if outcome == "failed":
                    self.message_user(
                        request,
                        "Status updated, but buyer email failed to send.",
                        level=messages.WARNING,
                    )
                return
        super().save_model(request, obj, form, change)


# ── Draft Admin (debugging) ─────────────────────────────────────


@admin.register(ApplicationDraft, site=sb_admin_site)
class ApplicationDraftAdmin(SBAdmin):
    list_display = (
        "token_short",
        "email",
        "program_type",
        "current_step",
        "submitted",
        "is_expired_display",
        "updated_at",
    )
    sbadmin_list_display = [
        SBAdminField(name="sb_token", title="Token", annotate=F("token")),
        "email",
        "program_type",
        "current_step",
        "submitted",
        SBAdminField(name="sb_expired", title="Expired?", annotate=F("expires_at")),
        "updated_at",
    ]
    list_filter = ("program_type", "current_step", "submitted")
    search_fields = ("email",)
    readonly_fields = (
        "token",
        "form_data",
        "created_at",
        "updated_at",
        "expires_at",
        "submitted",
        "submitted_at",
    )

    # ── SmartBase AG Grid methods ──

    def sb_token(self, obj_id, value, **kwargs):
        """SmartBase list: shortened token. `value` = token UUID."""
        if value is None:
            return "—"
        if hasattr(value, "hex"):
            return value.hex[:8]
        return str(value).replace("-", "")[:8]

    def sb_expired(self, obj_id, value, **kwargs):
        """SmartBase list: expired check. `value` = expires_at datetime."""
        if value is None:
            return False
        return timezone.now() >= value

    # ── Dual-compatible display methods ──

    @admin.display(description="Token", ordering="token")
    def token_short(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, ApplicationDraft):
            return obj_or_id.token.hex[:8]
        # SmartBase path
        if value is None:
            return "—"
        if hasattr(value, "hex"):
            return value.hex[:8]
        return str(value).replace("-", "")[:8]

    @admin.display(description="Expired?", boolean=True, ordering="expires_at")
    def is_expired_display(self, obj_or_id, value=None, **kwargs):
        if isinstance(obj_or_id, ApplicationDraft):
            return obj_or_id.is_expired
        # SmartBase path
        if value is None:
            return False
        return timezone.now() >= value
