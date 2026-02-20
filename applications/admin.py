"""
Admin configuration for the GCLBA Application Portal.

Uses Django Unfold for a modern staff dashboard with colored status badges,
organized fieldsets, inline documents, and automatic status audit logging.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Application, ApplicationDraft, Document, StatusLog

# ── Inlines ──────────────────────────────────────────────────────


class DocumentInline(TabularInline):
    model = Document
    extra = 0
    fields = ("doc_type", "file", "original_filename", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class StatusLogInline(TabularInline):
    model = StatusLog
    extra = 0
    fields = ("from_status", "to_status", "changed_by", "notes", "changed_at")
    readonly_fields = ("from_status", "to_status", "changed_by", "changed_at")


# ── Application Admin ────────────────────────────────────────────


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = (
        "reference_number",
        "full_name",
        "email",
        "property_address",
        "display_status",
        "display_docs",
        "assigned_to",
        "submitted_at",
    )
    list_filter = ("status", "program_type", "purchase_type", "assigned_to", "submitted_at")
    list_filter_submit = True
    search_fields = (
        "reference_number",
        "first_name",
        "last_name",
        "email",
        "property_address",
        "parcel_id",
    )
    readonly_fields = ("reference_number", "created_at", "updated_at", "submitted_at")
    inlines = [DocumentInline, StatusLogInline]

    fieldsets = (
        (
            "Reference",
            {
                "fields": ("reference_number", "status", "assigned_to"),
            },
        ),
        (
            "Section 1: Applicant Identity",
            {
                "fields": (
                    ("first_name", "last_name"),
                    "email",
                    "phone",
                    "preferred_contact",
                    "street_address",
                    ("city", "state", "zip_code"),
                ),
            },
        ),
        (
            "Section 2: Property Information",
            {
                "fields": (
                    "property_address",
                    "parcel_id",
                    "program_type",
                    "attended_open_house",
                    "open_house_date",
                ),
            },
        ),
        (
            "Section 3: Offer Details",
            {
                "fields": ("offer_amount", "purchase_type", "intended_use"),
            },
        ),
        (
            "Section 4: Eligibility",
            {
                "fields": ("has_delinquent_taxes", "has_tax_foreclosure"),
                "description": "If either is Yes, the applicant was disqualified but submitted anyway.",
            },
        ),
        (
            "Section 6: Rehab Plan",
            {
                "fields": (
                    "rehab_scope",
                    "rehab_budget",
                    "rehab_timeline",
                    "contractor_name",
                    "contractor_phone",
                ),
                "classes": ("collapse",),
                "description": "Only applicable for Ready for Rehab program.",
            },
        ),
        (
            "Section 7: Land Contract Details",
            {
                "fields": (
                    "lc_provider_name",
                    "lc_provider_phone",
                    "lc_term_months",
                    "lc_interest_rate",
                ),
                "classes": ("collapse",),
                "description": "Only applicable for Land Contract purchases.",
            },
        ),
        (
            "Section 8: Acknowledgments",
            {
                "fields": (
                    "ack_info_accurate",
                    "ack_terms_conditions",
                    "ack_inspection_waiver",
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

    @display(
        description="Status",
        label={
            Application.Status.SUBMITTED: "warning",
            Application.Status.UNDER_REVIEW: "warning",
            Application.Status.DOCS_REQUESTED: "info",
            Application.Status.APPROVED: "success",
            Application.Status.DENIED: "danger",
            Application.Status.WITHDRAWN: "info",
        },
    )
    def display_status(self, instance):
        return instance.status

    @display(description="Docs")
    def display_docs(self, instance):
        if instance.docs_complete:
            return "Complete"
        return "Incomplete"

    def save_model(self, request, obj, form, change):
        """Auto-create StatusLog when status changes."""
        if change:
            old_status = form.initial.get("status", "")
            new_status = obj.status
            if old_status != new_status:
                super().save_model(request, obj, form, change)
                StatusLog.objects.create(
                    application=obj,
                    from_status=old_status,
                    to_status=new_status,
                    changed_by=request.user,
                )
                return
        super().save_model(request, obj, form, change)


# ── Draft Admin (debugging) ─────────────────────────────────────


@admin.register(ApplicationDraft)
class ApplicationDraftAdmin(ModelAdmin):
    list_display = ("token_short", "email", "current_step", "is_expired_display", "updated_at")
    list_filter = ("current_step",)
    search_fields = ("email",)
    readonly_fields = ("token", "form_data", "created_at", "updated_at", "expires_at")

    def token_short(self, obj):
        return obj.token.hex[:8]

    token_short.short_description = "Token"

    def is_expired_display(self, obj):
        return obj.is_expired

    is_expired_display.short_description = "Expired?"
    is_expired_display.boolean = True
