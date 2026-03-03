"""
VIP Spotlight program forms.

Step path: Proposal → Documents → Acks (4-6)

VIP is a proposal process, not a standard offer. The buyer writes
narrative answers to 8 structured questions. There's no offer_amount
field - purchase price is stated within Q1.
"""

from django import forms

from ..models import Application
from .shared import BaseAcknowledgmentsForm


class VIPProposalForm(forms.Form):
    """
    VIP Spotlight proposal - 8 structured questions.

    Questions 1-6 are required. Q7 (contractor info) and Q8 (additional
    info) are optional. Q2 and Q5 have boolean + conditional detail fields.
    """

    # Q1: Who and why
    vip_q1_who_and_why = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        label=(
            "1. Who are you and why do you want to purchase this property? "
            "Include your proposed purchase price, contact information, and "
            "buyer/entity name."
        ),
    )

    # Q2: Prior GCLBA purchases
    vip_q2_prior_purchases = forms.NullBooleanField(
        widget=forms.RadioSelect(
            choices=[
                (True, "Yes"),
                (False, "No"),
            ]
        ),
        label="2. Have you purchased single-family homes from GCLBA previously?",
    )
    vip_q2_prior_detail = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="If yes, please provide details of prior GCLBA purchases",
    )

    # Q3: Renovation costs and timeline
    vip_q3_renovation_costs_timeline = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        label=(
            "3. What are your estimated renovation costs and development timeline? "
            "Please provide a detailed scope of work."
        ),
    )

    # Q4: Financing
    vip_q4_financing = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label=(
            "4. How do you intend to finance the project? Include proof of funds "
            "for the equity portion and pre-approval letters for construction "
            "loans if applicable."
        ),
    )

    # Q5: Experience
    vip_q5_has_experience = forms.NullBooleanField(
        widget=forms.RadioSelect(
            choices=[
                (True, "Yes"),
                (False, "No"),
            ]
        ),
        label="5. Do you have single-family home renovation experience?",
    )
    vip_q5_experience_detail = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
        label=(
            "If yes, please provide a portfolio: addresses of renovated homes, "
            "before/after photos"
        ),
    )

    # Q6: Completion plan
    vip_q6_completion_plan = forms.ChoiceField(
        choices=[("", "Select")] + list(Application.VIPCompletionPlan.choices),
        label="6. What are your plans upon completion?",
    )
    vip_q6_completion_detail = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Please provide details of your completion plan",
    )

    # Q7: Contractor info (optional)
    vip_q7_contractor_info = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label=(
            "7. Will you hire a contractor? If so, provide names and their "
            "Genesee County experience. (Optional)"
        ),
    )

    # Q8: Additional info (optional)
    vip_q8_additional_info = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label=(
            "8. Any additional information - letters of support, references, "
            "community ties. (Optional)"
        ),
    )

    def clean(self):
        cleaned = super().clean()

        # If Q2 is Yes, detail is required
        if cleaned.get("vip_q2_prior_purchases") is True and not cleaned.get(
            "vip_q2_prior_detail"
        ):
            self.add_error(
                "vip_q2_prior_detail",
                "Please provide details of your prior GCLBA purchases.",
            )

        # If Q5 is Yes, experience detail is required
        if cleaned.get("vip_q5_has_experience") is True and not cleaned.get(
            "vip_q5_experience_detail"
        ):
            self.add_error(
                "vip_q5_experience_detail",
                "Please provide your renovation portfolio details.",
            )

        return cleaned


class VIPAcknowledgmentsForm(BaseAcknowledgmentsForm):
    """
    Acknowledgments for VIP Spotlight - includes additional VIP-specific items.

    Inherits 4 shared acks from BaseAcknowledgmentsForm, adds:
    - Tax capture with VIP-specific label (mentions Brownfield abatements)
    - Reconveyance deed: property reverts if project not completed per agreement
    - No transfer: cannot transfer or encumber without prior GCLBA written consent

    Does NOT include ack_highest_not_guaranteed (VIP is proposal-based, not highest-offer).
    field_order keeps ack_info_accurate last for template iteration.
    """

    field_order = [
        "ack_sold_as_is",
        "ack_quit_claim_deed",
        "ack_no_title_insurance",
        "ack_tax_capture",
        "ack_reconveyance_deed",
        "ack_no_transfer",
        "ack_info_accurate",
    ]

    ack_tax_capture = forms.BooleanField(
        label=(
            "I understand any request to waive the Land Bank 5/50 tax capture must "
            "be made before the Land Bank accepts my offer. Seeking Brownfield or "
            "other abatements without a waiver conflicts with 5/50 tax roll."
        ),
    )
    ack_reconveyance_deed = forms.BooleanField(
        label=(
            "I acknowledge that I will sign a reconveyance deed at closing. The "
            "property will revert to GCLBA if the project is not completed per "
            "the Purchase & Development Agreement."
        ),
    )
    ack_no_transfer = forms.BooleanField(
        label=(
            "I will not transfer or encumber the property without prior written "
            "GCLBA consent until a Release of Interest is recorded."
        ),
    )
