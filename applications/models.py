"""
Models for the GCLBA Application Portal.

Four models:
- ApplicationDraft: Temporary storage for multi-step form (UUID token, JSONField)
- Application: Final submitted application with all flat fields for admin filtering
- Document: Typed file uploads (photo ID, pay stubs, bank statements, etc.)
- StatusLog: Audit trail for every status change
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ApplicationDraft(models.Model):
    """
    Temporary storage for a multi-step application form.

    Uses a UUID token for magic-link resume. Stores all form data
    in a JSONField so steps can be completed in any order. Expires
    after 14 days. Converted to a real Application on final submission.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(blank=True)
    form_data = models.JSONField(default=dict, blank=True)
    current_step = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        email_display = self.email or "no email"
        return f"Draft {self.token.hex[:8]} ({email_display}) — step {self.current_step}"

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
    sort, and search them. Sections mirror the 8-step buyer form.
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        DOCS_REQUESTED = "docs_requested", "Documents Requested"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        WITHDRAWN = "withdrawn", "Withdrawn"

    class ProgramType(models.TextChoices):
        OWN_IT_NOW = "own_it_now", "Own It Now"
        READY_FOR_REHAB = "ready_for_rehab", "Ready for Rehab"

    class PurchaseType(models.TextChoices):
        CASH = "cash", "Cash"
        LAND_CONTRACT = "land_contract", "Land Contract"
        CONVENTIONAL = "conventional", "Conventional Mortgage"
        FHA_VA = "fha_va", "FHA/VA Loan"

    class IntendedUse(models.TextChoices):
        PRIMARY_RESIDENCE = "primary_residence", "Primary Residence"
        RENTAL = "rental", "Rental Property"
        REHAB_RESALE = "rehab_resale", "Rehab & Resale"
        COMMERCIAL = "commercial", "Commercial Use"

    class PreferredContact(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        TEXT = "text", "Text"

    # ── Reference & Workflow ─────────────────────────────────────
    reference_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated: GCLBA-YYYY-NNNN",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications",
        help_text="Staff member reviewing this application",
    )

    # ── Section 1: Applicant Identity ────────────────────────────
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    preferred_contact = models.CharField(
        max_length=10,
        choices=PreferredContact.choices,
        default=PreferredContact.EMAIL,
    )
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, default="MI")
    zip_code = models.CharField(max_length=10)

    # ── Section 2: Property Info ─────────────────────────────────
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
        max_length=20,
        choices=ProgramType.choices,
        default=ProgramType.OWN_IT_NOW,
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

    # ── Section 3: Offer Details ─────────────────────────────────
    offer_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Purchase offer in dollars",
    )
    purchase_type = models.CharField(
        max_length=20,
        choices=PurchaseType.choices,
        default=PurchaseType.CASH,
    )
    intended_use = models.CharField(
        max_length=20,
        choices=IntendedUse.choices,
        default=IntendedUse.PRIMARY_RESIDENCE,
    )

    # ── Section 4: Eligibility ───────────────────────────────────
    has_delinquent_taxes = models.BooleanField(
        default=False,
        help_text="Does the buyer owe delinquent property taxes in Genesee County?",
    )
    has_tax_foreclosure = models.BooleanField(
        default=False,
        help_text="Has the buyer lost property to tax foreclosure in Genesee County?",
    )

    # ── Section 6: Rehab Plan (conditional: Ready for Rehab only) ─
    rehab_scope = models.TextField(
        blank=True,
        help_text="Description of planned rehabilitation work",
    )
    rehab_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated rehab budget in dollars",
    )
    rehab_timeline = models.CharField(
        max_length=100,
        blank=True,
        help_text="Expected timeline for rehab completion",
    )
    contractor_name = models.CharField(max_length=200, blank=True)
    contractor_phone = models.CharField(max_length=20, blank=True)

    # ── Section 7: Land Contract (conditional) ───────────────────
    lc_provider_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Land contract provider",
    )
    lc_provider_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Provider phone",
    )
    lc_term_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Contract term (months)",
    )
    lc_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Interest rate (%)",
    )

    # ── Section 8: Acknowledgments ───────────────────────────────
    ack_info_accurate = models.BooleanField(
        default=False,
        verbose_name="I certify all information is accurate",
    )
    ack_terms_conditions = models.BooleanField(
        default=False,
        verbose_name="I agree to GCLBA terms and conditions",
    )
    ack_inspection_waiver = models.BooleanField(
        default=False,
        verbose_name="I understand properties are sold as-is",
    )

    # ── Timestamps ───────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.reference_number} — {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def docs_complete(self):
        """Check if all required document types have been uploaded."""
        uploaded_types = set(self.documents.values_list("doc_type", flat=True))
        required = {"photo_id"}

        if self.purchase_type == self.PurchaseType.CASH:
            required.add("proof_of_funds")
        elif self.purchase_type == self.PurchaseType.LAND_CONTRACT:
            required |= {"pay_stub_1", "pay_stub_2", "bank_statement"}
        elif self.purchase_type in (
            self.PurchaseType.CONVENTIONAL,
            self.PurchaseType.FHA_VA,
        ):
            required.add("preapproval")

        return required.issubset(uploaded_types)

    @staticmethod
    def generate_reference_number():
        """Generate next GCLBA-YYYY-NNNN reference number."""
        year = timezone.now().year
        prefix = f"GCLBA-{year}-"
        last = (
            Application.objects.filter(reference_number__startswith=prefix)
            .order_by("-reference_number")
            .first()
        )
        if last:
            last_num = int(last.reference_number.split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        return f"{prefix}{next_num:04d}"


class Document(models.Model):
    """
    A typed document uploaded as part of an application.

    Document types are conditional on purchase_type:
    - Cash: photo_id + proof_of_funds
    - Land contract: photo_id + 2 pay stubs + bank statement
    - Conventional/FHA/VA: photo_id + preapproval letter
    """

    class DocType(models.TextChoices):
        PHOTO_ID = "photo_id", "Photo ID"
        PAY_STUB_1 = "pay_stub_1", "Pay Stub #1"
        PAY_STUB_2 = "pay_stub_2", "Pay Stub #2"
        BANK_STATEMENT = "bank_statement", "Bank Statement"
        PROOF_OF_FUNDS = "proof_of_funds", "Proof of Funds"
        PREAPPROVAL = "preapproval", "Pre-Approval Letter"
        ADDITIONAL_INCOME = "additional_income", "Additional Income Documentation"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    file = models.FileField(upload_to="applications/%Y/%m/")
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["doc_type"]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.application.reference_number}"


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

    def __str__(self):
        return (
            f"{self.application.reference_number}: {self.from_status or '(new)'} → {self.to_status}"
        )
