"""
Models for the GCLBA Application Portal.

Six models:
- User: Custom user model (always define at project start - changing later is painful)
- Property: Inventory of Land Bank properties loaded via CSV
- ApplicationDraft: Temporary storage for multi-step form (UUID token, JSONField)
- Application: Final submitted application with all flat fields for admin filtering
- Document: Typed file uploads per program requirements
- StatusLog: Audit trail for every status change
"""

import re
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model. Defined early so AUTH_USER_MODEL is set before
    first migration. Add staff-specific fields here as needed (e.g.
    department, phone extension, notification preferences).
    """

    class Meta:
        db_table = "auth_user"


class Property(models.Model):
    """
    A Land Bank property available for purchase.

    Populated via CSV import (weekly upload by staff). The normalized
    address field powers buyer-side autocomplete matching. Parcel ID
    is the unique identifier from Genesee County records.
    """

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNDER_OFFER = "under_offer", "Under Offer"
        SOLD = "sold", "Sold"
        WITHDRAWN = "withdrawn", "Withdrawn"

    address = models.CharField(
        max_length=255,
        help_text="Property address as it appears in the listing",
    )
    address_normalized = models.CharField(
        max_length=255,
        editable=False,
        unique=True,
        help_text="Lowercase, standardized abbreviations for fuzzy matching",
    )
    parcel_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Genesee County parcel ID number (null allowed for imports without parcel data)",
    )
    program_type = models.CharField(
        max_length=30,
        # Choices set after Application class is defined (forward reference)
        help_text="Which program this property is listed under",
    )
    listing_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Listed price in dollars (optional)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    csv_batch = models.CharField(
        max_length=100,
        blank=True,
        help_text="Identifier for the CSV import batch",
    )

    class Meta:
        ordering = ["address"]
        verbose_name_plural = "properties"
        indexes = [
            models.Index(
                fields=["program_type", "status"],
                name="idx_prop_program_status",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parcel_id"],
                condition=models.Q(parcel_id__isnull=False),
                name="unique_parcel_id_when_set",
            ),
        ]

    def __str__(self):
        if self.parcel_id:
            return f"{self.address} ({self.parcel_id})"
        return self.address

    def save(self, *args, **kwargs):
        self.address_normalized = self.normalize_address(self.address)
        super().save(*args, **kwargs)

    @staticmethod
    def normalize_address(address):
        """
        Normalize an address for consistent matching.

        Lowercases, strips extra whitespace, and standardizes common
        abbreviations (Street→st, Avenue→ave, etc.) so that
        '1234 Elm Street' matches '1234 elm st'.
        """
        if not address:
            return ""
        text = address.lower().strip()
        text = re.sub(r"\s+", " ", text)

        abbreviations = {
            "street": "st",
            "avenue": "ave",
            "boulevard": "blvd",
            "drive": "dr",
            "court": "ct",
            "place": "pl",
            "lane": "ln",
            "road": "rd",
            "circle": "cir",
            "north": "n",
            "south": "s",
            "east": "e",
            "west": "w",
            "northeast": "ne",
            "northwest": "nw",
            "southeast": "se",
            "southwest": "sw",
        }
        words = text.split()
        words = [abbreviations.get(w, w) for w in words]
        return " ".join(words)


# Fix forward reference - Property.program_type uses Application.ProgramType choices,
# but Application is defined below. We'll patch it after Application is defined.


class ApplicationDraft(models.Model):
    """
    Temporary storage for a multi-step application form.

    Uses a UUID token for magic-link resume. Stores all form data
    in a JSONField so steps can be completed in any order. Expires
    after 14 days. Converted to a real Application on final submission.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(blank=True)
    program_type = models.CharField(max_length=30, blank=True)
    form_data = models.JSONField(default=dict, blank=True)
    current_step = models.PositiveSmallIntegerField(default=1)
    submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        email_display = self.email or "no email"
        return f"Draft {self.token.hex[:8]} ({email_display}) - step {self.current_step}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class Application(models.Model):
    """
    A submitted GCLBA property purchase application.

    All fields are flat (not JSON) so the Unfold admin can filter,
    sort, and search them. Program type determines which fields are
    populated - VIP applications have proposal fields, R4R has
    line-item renovation costs, Featured Homes has narrative renovation.
    """

    # ── Choices ─────────────────────────────────────────────────

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        NEEDS_MORE_INFO = "needs_more_info", "Needs More Info"

    # Finite state machine: which transitions are legal from each status
    ALLOWED_TRANSITIONS = {
        "received": {"under_review"},
        "under_review": {"approved", "declined", "needs_more_info"},
        "needs_more_info": {"under_review"},
        "approved": set(),  # terminal
        "declined": {"under_review"},  # allow re-open
    }

    class ProgramType(models.TextChoices):
        FEATURED_HOMES = "featured_homes", "Featured Homes"
        READY_FOR_REHAB = "ready_for_rehab", "Ready for Rehab"
        VIP_SPOTLIGHT = "vip_spotlight", "VIP Spotlight"
        VACANT_LOT = "vacant_lot", "Vacant Lot"

    class PurchaseType(models.TextChoices):
        CASH = "cash", "Cash"
        LAND_CONTRACT = "land_contract", "Land Contract"

    class IntendedUse(models.TextChoices):
        RENOVATE_MOVE_IN = "renovate_move_in", "Renovate & Move In"
        RENOVATE_FAMILY = "renovate_family", "Renovate for Family Member"
        RENOVATE_SELL = "renovate_sell", "Renovate & Sell"
        RENOVATE_RENT = "renovate_rent", "Renovate & Rent Out"
        DEMOLISH = "demolish", "Demolish"

    class PreferredContact(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone Call"
        TEXT = "text", "Text"

    class FirstHomeOrMoving(models.TextChoices):
        FIRST_HOME = "first_home", "First Home Purchase"
        MOVING_TO_MI = "moving_to_mi", "Moving to MI from Another State"
        NEITHER = "neither", "Neither"

    class HomebuyerEdAgency(models.TextChoices):
        METRO_COMMUNITY_DEV = "metro_community_dev", "Metro Community Development"
        HABITAT_FOR_HUMANITY = "habitat_for_humanity", "Genesee County Habitat for Humanity"
        FANNIE_MAE_ONLINE = "fannie_mae_online", "Fannie Mae (Online)"
        OTHER = "other", "Other"

    class VIPCompletionPlan(models.TextChoices):
        SELL = "sell", "Sell"
        RENT = "rent", "Rent"

    # ── Reference & Workflow ────────────────────────────────────

    reference_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated: GCLBA-YYYY-NNNN",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications",
        help_text="Staff member reviewing this application",
    )
    staff_notes = models.TextField(
        blank=True,
        help_text="Internal notes - never visible to buyer",
    )

    # ── Section 1: Applicant Identity ───────────────────────────

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    preferred_contact = models.CharField(
        max_length=10,
        choices=PreferredContact.choices,
        default=PreferredContact.EMAIL,
    )
    mailing_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, default="MI")
    zip_code = models.CharField(max_length=10)
    purchasing_entity_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="If purchasing through an LLC, trust, or other entity",
    )
    contact_name_different = models.CharField(
        max_length=200,
        blank=True,
        help_text="If the primary contact is different from the buyer",
    )

    # ── Section 2: Property Info ────────────────────────────────

    property_ref = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
        help_text="Linked property from inventory (null if manually entered)",
    )
    property_address = models.CharField(
        max_length=255,
        blank=True,
        help_text="Address of the property being purchased",
    )
    parcel_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="County parcel ID number",
    )
    program_type = models.CharField(
        max_length=30,
        choices=ProgramType.choices,
        default=ProgramType.FEATURED_HOMES,
    )
    attended_open_house = models.BooleanField(
        default=False,
        help_text="Has the buyer visited the property?",
    )
    open_house_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of open house visit",
    )

    # ── Section 3: Eligibility Gate ─────────────────────────────

    has_delinquent_taxes = models.BooleanField(
        default=False,
        help_text="Does the buyer owe delinquent property taxes in Genesee County?",
    )
    has_tax_foreclosure = models.BooleanField(
        default=False,
        help_text="Has the buyer lost property to tax foreclosure in Genesee County?",
    )

    # ── Section 4: Offer Details (Featured Homes + R4R) ─────────

    offer_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Purchase offer in dollars",
    )
    purchase_type = models.CharField(
        max_length=20,
        choices=PurchaseType.choices,
        default=PurchaseType.CASH,
    )
    down_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Land contract down payment (min 10% or $1,000)",
    )
    is_self_employed = models.BooleanField(
        default=False,
        help_text="Changes income documentation requirements for land contract",
    )

    # ── Renovation Narrative (Featured Homes + R4R) ─────────────

    intended_use = models.CharField(
        max_length=20,
        choices=IntendedUse.choices,
        blank=True,
    )
    first_home_or_moving = models.CharField(
        max_length=20,
        choices=FirstHomeOrMoving.choices,
        blank=True,
        help_text="Sub-question when intended use is Renovate & Move In",
    )
    renovation_description = models.TextField(
        blank=True,
        help_text="What renovations will you be making?",
    )
    renovation_who = models.TextField(
        blank=True,
        help_text="Who will complete the renovations?",
    )
    renovation_when = models.CharField(
        max_length=200,
        blank=True,
        help_text="When will renovations be completed?",
    )
    renovation_funding = models.TextField(
        blank=True,
        help_text="How will you pay for purchase and renovations?",
    )

    # ── R4R Line-Item Renovation Costs ──────────────────────────

    # Interior costs
    reno_clean_out = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_demolition_disposal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_hvac = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_water_heater = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_plumbing = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_electrical = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_kitchen_cabinets = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_kitchen_appliances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_bathroom_repairs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_flooring = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_doors_int = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_insulation = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_drywall_plaster = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_paint_wallpaper = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_lighting_int = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_interior_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Exterior costs
    reno_cleanup_landscaping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_roof = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_foundation = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_doors_ext = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_windows = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_siding = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_masonry = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_porch_decking = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_lighting_ext = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_garage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reno_exterior_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Total
    reno_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ── R4R Prior GCLBA Purchase ────────────────────────────────

    has_prior_gclba_purchase = models.BooleanField(
        default=False,
        help_text="Has applicant previously purchased from GCLBA?",
    )

    # ── Homebuyer Education (Land Contract Only) ────────────────

    homebuyer_ed_completed = models.BooleanField(
        default=False,
        help_text="Has completed or will complete homebuyer education before closing",
    )
    homebuyer_ed_agency = models.CharField(
        max_length=50,
        choices=HomebuyerEdAgency.choices,
        blank=True,
    )
    homebuyer_ed_other = models.CharField(
        max_length=200,
        blank=True,
        help_text="Agency name if Other selected",
    )

    # ── VIP Spotlight Proposal Questions ────────────────────────

    vip_q1_who_and_why = models.TextField(
        blank=True,
        help_text="Who are you and why do you want to purchase this property?",
    )
    vip_q2_prior_purchases = models.BooleanField(
        null=True,
        blank=True,
        help_text="Have you purchased single-family homes from GCLBA previously?",
    )
    vip_q2_prior_detail = models.TextField(
        blank=True,
        help_text="Details of prior GCLBA purchases",
    )
    vip_q3_renovation_costs_timeline = models.TextField(
        blank=True,
        help_text="Estimated renovation costs and development timeline",
    )
    vip_q4_financing = models.TextField(
        blank=True,
        help_text="How do you intend to finance the project?",
    )
    vip_q5_has_experience = models.BooleanField(
        null=True,
        blank=True,
        help_text="Do you have single-family home renovation experience?",
    )
    vip_q5_experience_detail = models.TextField(
        blank=True,
        help_text="Portfolio: addresses, before/after photos",
    )
    vip_q6_completion_plan = models.CharField(
        max_length=20,
        choices=VIPCompletionPlan.choices,
        blank=True,
        help_text="Plans upon completion - sell or rent?",
    )
    vip_q6_completion_detail = models.TextField(
        blank=True,
        help_text="Details of completion plan",
    )
    vip_q7_contractor_info = models.TextField(
        blank=True,
        help_text="Contractor names and Genesee County experience",
    )
    vip_q8_additional_info = models.TextField(
        blank=True,
        help_text="Letters of support, references, community ties",
    )

    # ── Acknowledgments ─────────────────────────────────────────

    ack_sold_as_is = models.BooleanField(
        default=False,
        verbose_name="I understand properties are sold as-is",
    )
    ack_quit_claim_deed = models.BooleanField(
        default=False,
        verbose_name="I understand closing is via Quit Claim Deed",
    )
    ack_no_title_insurance = models.BooleanField(
        default=False,
        verbose_name="I understand GCLBA does not provide title insurance",
    )
    ack_highest_not_guaranteed = models.BooleanField(
        default=False,
        verbose_name="I understand the highest offer is not guaranteed to be accepted",
    )
    ack_info_accurate = models.BooleanField(
        default=False,
        verbose_name="I certify all information is accurate",
    )
    ack_tax_capture = models.BooleanField(
        default=False,
        verbose_name="I understand the 5/50 tax capture waiver requirement",
    )
    # VIP only
    ack_reconveyance_deed = models.BooleanField(
        default=False,
        verbose_name="I acknowledge the reconveyance deed requirement",
    )
    ack_no_transfer = models.BooleanField(
        default=False,
        verbose_name="I will not transfer or encumber without GCLBA consent",
    )

    # ── Timestamps ──────────────────────────────────────────────

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            # Staff dashboard: filter by status (most common filter)
            models.Index(fields=["status"], name="idx_app_status"),
            # Staff dashboard: filter by status + program together
            models.Index(fields=["status", "program_type"], name="idx_app_status_program"),
            # Staff dashboard: sort by submission date
            models.Index(fields=["-submitted_at"], name="idx_app_submitted"),
            # Buyer lookup by email (for resume/status check)
            models.Index(fields=["email"], name="idx_app_email"),
        ]

    def __str__(self):
        return f"{self.reference_number} - {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def formatted_phone(self):
        digits = "".join(c for c in (self.phone or "") if c.isdigit())
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return self.phone or ""

    # ── Interior line-item field names (for calculation) ────────

    INTERIOR_RENO_FIELDS = [
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
    ]

    EXTERIOR_RENO_FIELDS = [
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
    ]

    def calculate_renovation_totals(self):
        """Calculate and store renovation subtotals and total. Call before save()."""
        self.reno_interior_subtotal = sum(
            getattr(self, f) or Decimal("0") for f in self.INTERIOR_RENO_FIELDS
        )
        self.reno_exterior_subtotal = sum(
            getattr(self, f) or Decimal("0") for f in self.EXTERIOR_RENO_FIELDS
        )
        self.reno_total = self.reno_interior_subtotal + self.reno_exterior_subtotal

    def clean(self):
        """Cross-field validation for program-specific rules."""
        errors = {}

        # Down payment validation for land contract
        if (
            self.purchase_type == self.PurchaseType.LAND_CONTRACT
            and self.offer_amount
            and self.down_payment_amount is not None
        ):
            min_down = max(self.offer_amount * Decimal("0.10"), Decimal("1000.00"))
            if self.down_payment_amount < min_down:
                errors["down_payment_amount"] = (
                    f"Minimum down payment is ${min_down:,.2f} "
                    f"(10% of offer or $1,000, whichever is higher)"
                )

        # Land contract only available for Featured Homes
        if (
            self.purchase_type == self.PurchaseType.LAND_CONTRACT
            and self.program_type != self.ProgramType.FEATURED_HOMES
        ):
            errors["purchase_type"] = "Land contract is only available for Featured Homes."

        # Land contract requires owner-occupied intent
        if self.purchase_type == self.PurchaseType.LAND_CONTRACT and self.intended_use in (
            self.IntendedUse.RENOVATE_SELL,
            self.IntendedUse.RENOVATE_RENT,
        ):
            errors["intended_use"] = (
                "Land contract is only available for owner-occupied properties."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def docs_complete(self):
        """Check if all required document types have been uploaded, per program."""
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "documents" in prefetched:
            uploaded_types = {doc.doc_type for doc in prefetched["documents"]}
        else:
            uploaded_types = set(self.documents.values_list("doc_type", flat=True))
        required = {"photo_id"}

        if self.program_type == self.ProgramType.FEATURED_HOMES:
            if self.purchase_type == self.PurchaseType.CASH:
                required.add("proof_of_funds")
            else:  # land contract
                required |= {"proof_of_income", "proof_of_down_payment"}
        elif self.program_type == self.ProgramType.READY_FOR_REHAB:
            required |= {"proof_of_funds", "reno_funding_proof"}
            if self.has_prior_gclba_purchase:
                required.add("prior_investment_proof")
        elif self.program_type == self.ProgramType.VIP_SPOTLIGHT:
            required.add("proof_of_funds")

        return required.issubset(uploaded_types)

    @staticmethod
    def generate_reference_number():
        """
        Generate next GCLBA-YYYY-NNNN reference number.

        Uses select_for_update() inside a transaction to prevent race
        conditions when two applications are submitted simultaneously.
        """
        from django.db import transaction

        with transaction.atomic():
            year = timezone.now().year
            prefix = f"GCLBA-{year}-"
            last = (
                Application.objects.select_for_update()
                .filter(reference_number__startswith=prefix)
                .order_by("-reference_number")
                .first()
            )
            if last:
                last_num = int(last.reference_number.split("-")[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            return f"{prefix}{next_num:04d}"


# Patch forward reference: Property.program_type uses Application's ProgramType choices
Property._meta.get_field("program_type").choices = Application.ProgramType.choices


class Document(models.Model):
    """
    A typed document uploaded as part of an application.

    Document types are conditional on program + purchase type.
    VIP portfolio photos and support letters allow multiple uploads.
    """

    class DocType(models.TextChoices):
        PHOTO_ID = "photo_id", "Photo ID"
        PROOF_OF_FUNDS = "proof_of_funds", "Proof of Funds"
        PROOF_OF_INCOME = "proof_of_income", "Proof of Income"
        PROOF_OF_DOWN_PAYMENT = "proof_of_down_payment", "Proof of Down Payment"
        RENO_FUNDING_PROOF = "reno_funding_proof", "Renovation Funding Documentation"
        PRIOR_INVESTMENT_PROOF = "prior_investment_proof", "Prior GCLBA Investment Proof"
        VIP_PREAPPROVAL = "vip_preapproval", "Pre-Approval Letter"
        VIP_PORTFOLIO_PHOTO = "vip_portfolio_photo", "Portfolio Photo"
        VIP_SUPPORT_LETTER = "vip_support_letter", "Letter of Support"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=50, choices=DocType.choices)
    file = models.FileField(upload_to="applications/%Y/%m/")
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["doc_type"]

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.application.reference_number}"


class StatusLog(models.Model):
    """
    Audit trail for application status changes.

    Auto-created by admin save_model override whenever status changes.
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    # Map raw status values to human-readable labels for the timeline.
    _STATUS_LABELS = dict(Application.Status.choices)

    @property
    def from_status_label(self):
        return self._STATUS_LABELS.get(self.from_status, self.from_status or "New")

    @property
    def to_status_label(self):
        return self._STATUS_LABELS.get(self.to_status, self.to_status)

    def __str__(self):
        return (
            f"{self.application.reference_number}: "
            f"{self.from_status or '(new)'} → {self.to_status}"
        )
