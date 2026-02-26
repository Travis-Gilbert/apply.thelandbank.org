"""
Admin configuration for the GCLBA Application Portal.

Uses Django Unfold for a modern staff dashboard with colored status badges,
organized fieldsets, inline documents, and automatic status audit logging.
"""

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .csv_import import import_properties_from_csv
from .models import Application, ApplicationDraft, Document, Property, StatusLog, User
from .status_notifications import requires_transition_note, send_buyer_status_email


# ── User Admin (required for autocomplete_fields on assigned_to) ──


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Custom User admin inheriting from both Django's UserAdmin and Unfold's ModelAdmin."""

    pass


# ── Property Admin ───────────────────────────────────────────────


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = (
        "address",
        "parcel_id",
        "display_program",
        "display_status",
        "listing_price_display",
        "application_count",
        "imported_at",
    )
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

    @display(
        description="Program",
        label={
            Application.ProgramType.FEATURED_HOMES: "success",
            Application.ProgramType.READY_FOR_REHAB: "warning",
            Application.ProgramType.VIP_SPOTLIGHT: "info",
            Application.ProgramType.VACANT_LOT: "info",
        },
    )
    def display_program(self, instance):
        return instance.program_type

    @display(
        description="Status",
        label={
            Property.Status.AVAILABLE: "success",
            Property.Status.UNDER_OFFER: "warning",
            Property.Status.SOLD: "info",
            Property.Status.WITHDRAWN: "danger",
        },
    )
    def display_status(self, instance):
        return instance.status

    @display(description="Price")
    def listing_price_display(self, instance):
        if instance.listing_price is None:
            return "N/A"
        return f"${instance.listing_price:,.2f}"

    @display(description="Apps", ordering="_application_count")
    def application_count(self, instance):
        return instance._application_count

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


class DocumentInline(TabularInline):
    model = Document
    extra = 0
    fields = ("doc_type", "file", "view_file", "original_filename", "uploaded_at")
    readonly_fields = ("view_file", "uploaded_at")

    @display(description="View")
    def view_file(self, instance):
        if not instance.pk or not instance.file:
            return "N/A"
        url = reverse("applications:document_view", args=[instance.pk])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Open</a>',
            url,
        )


class StatusLogInline(TabularInline):
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


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
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
        "full_name",
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
    list_filter = (
        "status",
        "program_type",
        "purchase_type",
        "assigned_to",
        DocsStateFilter,
        "submitted_at",
    )
    list_display_links = ("reference_number", "full_name")
    list_filter_submit = True
    date_hierarchy = "submitted_at"
    ordering = ("status", "-submitted_at")
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

    @display(description="Status", ordering="status")
    def display_status(self, instance):
        palette = {
            Application.Status.RECEIVED: ("#dbeafe", "#1e40af"),
            Application.Status.UNDER_REVIEW: ("#fef3c7", "#92400e"),
            Application.Status.NEEDS_MORE_INFO: ("#ffedd5", "#9a3412"),
            Application.Status.APPROVED: ("#dcfce7", "#166534"),
            Application.Status.DECLINED: ("#fee2e2", "#991b1b"),
        }
        bg, fg = palette.get(instance.status, ("#e5e7eb", "#374151"))
        return format_html(
            (
                "<span style='display:inline-flex;align-items:center;padding:2px 8px;"
                "border-radius:999px;font-size:12px;font-weight:600;"
                "background:{};color:{}'>{}</span>"
            ),
            bg,
            fg,
            instance.get_status_display(),
        )

    @display(description="Program")
    def display_program(self, instance):
        return instance.get_program_type_display()

    @display(description="Purchase Type", ordering="purchase_type")
    def display_purchase_type(self, instance):
        if instance.program_type == Application.ProgramType.VIP_SPOTLIGHT:
            return "Proposal"
        return instance.get_purchase_type_display()

    @display(description="Offer")
    def display_offer(self, instance):
        if instance.program_type == Application.ProgramType.VIP_SPOTLIGHT:
            return "See Proposal"
        if instance.offer_amount is None:
            return "N/A"
        return f"${instance.offer_amount:,.2f}"

    @display(description="Docs", label={"Complete": "success", "Incomplete": "danger"})
    def display_docs(self, instance):
        if instance.docs_complete:
            return "Complete"
        return "Incomplete"

    @display(description="Quick Docs")
    def quick_docs(self, instance):
        docs = list(instance.documents.all())
        if not docs:
            return "N/A"

        links_html = format_html_join(
            " ",
            (
                "<a href='{}' target='_blank' rel='noopener' title='{}' style="
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
        if len(docs) > 2:
            return format_html(
                "{} <span style='color:#6b7280;font-size:11px'>+{} more</span>",
                links_html,
                len(docs) - 2,
            )
        return links_html

    @display(description="Assigned", ordering="assigned_to__username")
    def display_assignee(self, instance):
        if not instance.assigned_to:
            return "Unassigned"
        return instance.assigned_to.get_full_name() or instance.assigned_to.get_username()

    @display(description="Age", ordering="submitted_at")
    def submitted_age(self, instance):
        days_open = (timezone.now() - instance.submitted_at).days
        if days_open == 0:
            return "Today"
        label = f"{days_open} day" if days_open == 1 else f"{days_open} days"
        if (
            instance.status in (Application.Status.RECEIVED, Application.Status.UNDER_REVIEW)
            and days_open >= 7
        ):
            return format_html("<span style='color:#b91c1c;font-weight:600'>{}</span>", label)
        return label

    @display(description="Closing Fee")
    def closing_fee_display(self, instance):
        if instance.program_type == Application.ProgramType.FEATURED_HOMES:
            if instance.purchase_type == Application.PurchaseType.LAND_CONTRACT:
                return "$125"
            return "$75"
        if instance.program_type == Application.ProgramType.READY_FOR_REHAB:
            return "$75"
        if instance.program_type == Application.ProgramType.VIP_SPOTLIGHT:
            return "Per Purchase & Development Agreement"
        return "TBD"

    def _bulk_set_status(self, request, queryset, new_status):
        apps = list(queryset.only(
            "id",
            "status",
            "staff_notes",
            "reference_number",
            "first_name",
            "email",
            "property_address",
            "program_type",
            "purchase_type",
            "offer_amount",
        ))
        changed = [app for app in apps if app.status != new_status]
        if not changed:
            self.message_user(request, "No status changes were needed.")
            return

        skipped_missing_note = []
        eligible = []
        for app in changed:
            note = (app.staff_notes or "").strip()
            if requires_transition_note(new_status) and not note:
                skipped_missing_note.append(app.reference_number)
                continue
            eligible.append(app)

        if not eligible:
            self.message_user(
                request,
                "No updates applied. Add a staff note before using this status action.",
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

        msg = f"Updated {len(ids)} application(s)."
        if skipped_missing_note:
            msg += f" Skipped {len(skipped_missing_note)} without required notes."
        if email_failures:
            msg += f" {email_failures} buyer status email(s) failed."

        level = messages.WARNING if skipped_missing_note or email_failures else messages.SUCCESS
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

    @admin.action(description="Assign selected to me")
    def assign_to_me(self, request, queryset):
        updated = queryset.exclude(assigned_to=request.user).update(
            assigned_to=request.user,
            updated_at=timezone.now(),
        )
        self.message_user(request, f"Assigned {updated} application(s) to you.")

    @admin.action(description="Clear assignee")
    def clear_assignee(self, request, queryset):
        updated = queryset.exclude(assigned_to=None).update(
            assigned_to=None,
            updated_at=timezone.now(),
        )
        self.message_user(request, f"Cleared assignee for {updated} application(s).")

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


@admin.register(ApplicationDraft)
class ApplicationDraftAdmin(ModelAdmin):
    list_display = (
        "token_short",
        "email",
        "program_type",
        "current_step",
        "submitted",
        "is_expired_display",
        "updated_at",
    )
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

    def token_short(self, obj):
        return obj.token.hex[:8]

    token_short.short_description = "Token"

    def is_expired_display(self, obj):
        return obj.is_expired

    is_expired_display.short_description = "Expired?"
    is_expired_display.boolean = True
    form = ApplicationAdminForm
