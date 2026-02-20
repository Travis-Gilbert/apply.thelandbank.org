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
        "property_address",
        "display_program",
        "display_status",
        "display_docs",
        "submitted_at",
    )
    list_filter = ("status", "program_type", "purchase_type", "submitted_at")
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
            "Reference & Status",
            {
                "fields": ("reference_number", "status", "staff_notes"),
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
            "R4R: Renovation Line Items — Interior",
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
            "R4R: Renovation Line Items — Exterior",
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

    @display(
        description="Status",
        label={
            Application.Status.RECEIVED: "info",
            Application.Status.UNDER_REVIEW: "warning",
            Application.Status.APPROVED: "success",
            Application.Status.DECLINED: "danger",
            Application.Status.NEEDS_MORE_INFO: "warning",
        },
    )
    def display_status(self, instance):
        return instance.status

    @display(description="Program")
    def display_program(self, instance):
        return instance.get_program_type_display()

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
    list_display = ("token_short", "email", "program_type", "current_step", "is_expired_display", "updated_at")
    list_filter = ("program_type", "current_step")
    search_fields = ("email",)
    readonly_fields = ("token", "form_data", "created_at", "updated_at", "expires_at")

    def token_short(self, obj):
        return obj.token.hex[:8]

    token_short.short_description = "Token"

    def is_expired_display(self, obj):
        return obj.is_expired

    is_expired_display.short_description = "Expired?"
    is_expired_display.boolean = True
