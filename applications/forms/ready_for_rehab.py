"""
Ready for Rehab program forms.

Step path: Offer → Documents → Line Items → Renovation Narrative → Acks (4-8)

Key differences from Featured Homes:
- Cash ONLY (no purchase_type choice)
- Line-item renovation cost estimate required
- Prior GCLBA purchase question + conditional document
"""

from decimal import Decimal

from django import forms

from ..models import Application


class R4ROfferForm(forms.Form):
    """
    Offer details for Ready for Rehab - cash only, no purchase type choice.

    The purchase_type is set automatically to "cash" in the view.
    Also collects the prior GCLBA purchase flag.
    """

    offer_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("1.00"),
        label="Offer Amount ($)",
    )
    has_prior_gclba_purchase = forms.BooleanField(
        required=False,
        label="I have previously purchased property from GCLBA",
        help_text="If yes, you will need to provide proof of investment in your prior purchase",
    )


class R4RLineItemsForm(forms.Form):
    """
    Line-item renovation cost estimate for Ready for Rehab.

    25 individual cost fields plus auto-calculated subtotals and total.
    All fields default to 0 and are optional (required=False) so the buyer
    only fills in trades that apply. The view/HTMX calculates subtotals
    client-side; the submission view recalculates server-side before saving.
    """

    # Interior costs
    reno_clean_out = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Clean Out",
    )
    reno_demolition_disposal = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Demolition & Disposal",
    )
    reno_hvac = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="HVAC",
    )
    reno_water_heater = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Water Heater",
    )
    reno_plumbing = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Plumbing",
    )
    reno_electrical = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Electrical",
    )
    reno_kitchen_cabinets = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Kitchen Cabinets",
    )
    reno_kitchen_appliances = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Kitchen Appliances",
    )
    reno_bathroom_repairs = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Bathroom Repairs",
    )
    reno_flooring = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Flooring & Floor Covering",
    )
    reno_doors_int = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Interior Doors",
    )
    reno_insulation = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Insulation",
    )
    reno_drywall_plaster = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Drywall & Plaster",
    )
    reno_paint_wallpaper = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Paint & Wallpaper",
    )
    reno_lighting_int = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Interior Lighting",
    )

    # Exterior costs
    reno_cleanup_landscaping = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Clean Up & Landscaping",
    )
    reno_roof = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Roof",
    )
    reno_foundation = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Foundation",
    )
    reno_doors_ext = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Exterior Doors",
    )
    reno_windows = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Windows",
    )
    reno_siding = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Siding",
    )
    reno_masonry = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Masonry",
    )
    reno_porch_decking = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Porch or Decking",
    )
    reno_lighting_ext = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Exterior Lighting",
    )
    reno_garage = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        label="Garage Repair or Demolition",
    )

    # Field groupings for template rendering and HTMX totals
    INTERIOR_FIELDS = [
        "reno_clean_out", "reno_demolition_disposal", "reno_hvac",
        "reno_water_heater", "reno_plumbing", "reno_electrical",
        "reno_kitchen_cabinets", "reno_kitchen_appliances",
        "reno_bathroom_repairs", "reno_flooring", "reno_doors_int",
        "reno_insulation", "reno_drywall_plaster", "reno_paint_wallpaper",
        "reno_lighting_int",
    ]

    EXTERIOR_FIELDS = [
        "reno_cleanup_landscaping", "reno_roof", "reno_foundation",
        "reno_doors_ext", "reno_windows", "reno_siding", "reno_masonry",
        "reno_porch_decking", "reno_lighting_ext", "reno_garage",
    ]

    def interior_fields(self):
        """Yield (name, field) tuples for interior cost fields."""
        for name in self.INTERIOR_FIELDS:
            yield name, self[name]

    def exterior_fields(self):
        """Yield (name, field) tuples for exterior cost fields."""
        for name in self.EXTERIOR_FIELDS:
            yield name, self[name]

    def calculate_totals(self):
        """
        Calculate subtotals and total from cleaned_data.

        Returns dict with interior_subtotal, exterior_subtotal, total.
        Called by the view after is_valid() to store computed values.
        """
        data = self.cleaned_data
        interior = sum(
            data.get(f) or Decimal("0") for f in self.INTERIOR_FIELDS
        )
        exterior = sum(
            data.get(f) or Decimal("0") for f in self.EXTERIOR_FIELDS
        )
        return {
            "reno_interior_subtotal": interior,
            "reno_exterior_subtotal": exterior,
            "reno_total": interior + exterior,
        }


class R4RRenovationNarrativeForm(forms.Form):
    """
    Renovation narrative for Ready for Rehab.

    Intended use + sub-question, then four open-ended questions.
    Defined separately from FH so each program can evolve independently.
    """

    intended_use = forms.ChoiceField(
        choices=Application.IntendedUse.choices,
        label="How do you plan to use this property?",
    )
    first_home_or_moving = forms.ChoiceField(
        choices=[("", "Select")] + list(Application.FirstHomeOrMoving.choices),
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

        if (
            intended_use == Application.IntendedUse.RENOVATE_MOVE_IN
            and not cleaned.get("first_home_or_moving")
        ):
            self.add_error(
                "first_home_or_moving",
                "Please indicate if this is a first home purchase or relocation.",
            )

        return cleaned


class R4RAcknowledgmentsForm(forms.Form):
    """
    Acknowledgments for Ready for Rehab - same as Featured Homes.

    Includes ack_highest_not_guaranteed (relevant for offer-based programs).
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
