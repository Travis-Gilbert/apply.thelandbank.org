"""
Featured Homes program forms.

Step path (cash):          Offer → Documents → Renovation → Acks (4-7)
Step path (land contract): Offer → Documents → Renovation → Homebuyer Ed → Acks (4-8)
"""

from decimal import Decimal

from django import forms

from ..models import Application
from .shared import BaseAcknowledgmentsForm, BaseRenovationNarrativeForm


class FHOfferForm(forms.Form):
    """
    Offer details for Featured Homes.

    Purchase type determines sub-fields:
    - Cash: just offer amount
    - Land Contract: offer + down payment + self-employed flag
    Down payment minimum validated server-side and shown client-side via HTMX.
    """

    offer_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("1.00"),
        label="Offer Amount ($)",
        widget=forms.NumberInput(attrs={"placeholder": "Enter amount", "inputmode": "decimal"}),
    )
    purchase_type = forms.ChoiceField(
        choices=Application.PurchaseType.choices,
        widget=forms.RadioSelect,
        label="How will you finance this purchase?",
    )
    down_payment_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Down Payment Amount ($)",
        help_text="Minimum: 10% of offer or $1,000, whichever is higher",
        widget=forms.NumberInput(attrs={"placeholder": "Enter amount", "inputmode": "decimal"}),
    )
    is_self_employed = forms.BooleanField(
        required=False,
        label="I am self-employed",
        help_text="This changes income documentation requirements",
    )

    def clean(self):
        cleaned = super().clean()
        purchase_type = cleaned.get("purchase_type")
        offer_amount = cleaned.get("offer_amount")
        down_payment = cleaned.get("down_payment_amount")

        if purchase_type == Application.PurchaseType.LAND_CONTRACT:
            # Down payment required for land contract
            if not down_payment:
                self.add_error(
                    "down_payment_amount",
                    "Down payment is required for land contract purchases.",
                )
            elif offer_amount:
                min_down = max(offer_amount * Decimal("0.10"), Decimal("1000.00"))
                if down_payment < min_down:
                    self.add_error(
                        "down_payment_amount",
                        f"Minimum down payment is ${min_down:,.2f} "
                        f"(10% of offer or $1,000, whichever is higher).",
                    )

        return cleaned


# FH and R4R renovation narratives are identical (same 6 fields, same validation).
FHRenovationNarrativeForm = BaseRenovationNarrativeForm


class FHHomebuyerEdForm(forms.Form):
    """
    Homebuyer education - Featured Homes land contract only.

    Required before closing. MSHDA or HUD approved counselors.
    """

    homebuyer_ed_completed = forms.BooleanField(
        required=False,
        label="I have completed (or will complete before closing) a homebuyer education course",
    )
    homebuyer_ed_agency = forms.ChoiceField(
        choices=[("", "Select Agency")] + list(Application.HomebuyerEdAgency.choices),
        required=False,
        label="Homebuyer Education Provider",
    )
    homebuyer_ed_other = forms.CharField(
        max_length=200,
        required=False,
        label="Other Agency Name",
        help_text="If you selected 'Other' above",
    )


class FHAcknowledgmentsForm(BaseAcknowledgmentsForm):
    """
    Acknowledgments for Featured Homes — standard set.

    Inherits 4 shared acks from BaseAcknowledgmentsForm, adds
    ack_highest_not_guaranteed + ack_tax_capture for offer-based programs.
    field_order keeps ack_info_accurate last for template iteration.
    """

    field_order = [
        "ack_sold_as_is",
        "ack_quit_claim_deed",
        "ack_no_title_insurance",
        "ack_highest_not_guaranteed",
        "ack_tax_capture",
        "ack_info_accurate",
    ]

    ack_highest_not_guaranteed = forms.BooleanField(
        label="I understand the highest offer is not guaranteed to be accepted.",
    )
    ack_tax_capture = forms.BooleanField(
        label=(
            "I understand any request to waive the Land Bank 5/50 tax capture must "
            "be made before the Land Bank accepts my offer. Otherwise the request "
            "will not be considered."
        ),
    )
