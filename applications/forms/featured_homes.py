"""
Featured Homes program forms.

Step path (cash):          Offer → Documents → Renovation → Acks (4-7)
Step path (land contract): Offer → Documents → Renovation → Homebuyer Ed → Acks (4-8)
"""

from decimal import Decimal

from django import forms

from ..models import Application


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


class FHRenovationNarrativeForm(forms.Form):
    """
    Renovation narrative for Featured Homes.

    Intended use + sub-question, then four open-ended questions about
    renovation plans, timeline, who performs the work, and how it's funded.
    """

    intended_use = forms.ChoiceField(
        choices=Application.IntendedUse.choices,
        label="How do you plan to use this property?",
    )
    first_home_or_moving = forms.ChoiceField(
        choices=[("", "— Select —")] + list(Application.FirstHomeOrMoving.choices),
        required=False,
        label="Is this your first home purchase, or are you moving to Michigan?",
    )
    renovation_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="What renovations will you be making?",
    )
    renovation_who = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Who will complete the renovations?",
    )
    renovation_when = forms.CharField(
        max_length=200,
        label="When will renovations be completed?",
    )
    renovation_funding = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="How will you pay for the purchase and renovations?",
    )

    def clean(self):
        cleaned = super().clean()
        intended_use = cleaned.get("intended_use")

        # first_home_or_moving only relevant when intended_use is RENOVATE_MOVE_IN
        if (
            intended_use == Application.IntendedUse.RENOVATE_MOVE_IN
            and not cleaned.get("first_home_or_moving")
        ):
            self.add_error(
                "first_home_or_moving",
                "Please indicate if this is a first home purchase or relocation.",
            )

        return cleaned


class FHHomebuyerEdForm(forms.Form):
    """
    Homebuyer education — Featured Homes land contract only.

    Required before closing. MSHDA or HUD approved counselors.
    """

    homebuyer_ed_completed = forms.BooleanField(
        required=False,
        label="I have completed (or will complete before closing) a homebuyer education course",
    )
    homebuyer_ed_agency = forms.ChoiceField(
        choices=[("", "— Select Agency —")] + list(Application.HomebuyerEdAgency.choices),
        required=False,
        label="Homebuyer Education Provider",
    )
    homebuyer_ed_other = forms.CharField(
        max_length=200,
        required=False,
        label="Other Agency Name",
        help_text="If you selected 'Other' above",
    )


class FHAcknowledgmentsForm(forms.Form):
    """
    Acknowledgments for Featured Homes — standard set.

    All are required checkboxes. The buyer must affirmatively agree to each.
    """

    ack_sold_as_is = forms.BooleanField(
        label=(
            "I understand that all GCLBA properties are sold as-is and I have "
            "had the opportunity to inspect the property."
        ),
    )
    ack_quit_claim_deed = forms.BooleanField(
        label="I understand closing is via Quit Claim Deed.",
    )
    ack_no_title_insurance = forms.BooleanField(
        label="I understand GCLBA does not provide title insurance.",
    )
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
    ack_info_accurate = forms.BooleanField(
        label="I certify that all information provided in this application is true and accurate.",
    )
