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
from .featured_homes import FHAcknowledgmentsForm
from .shared import BaseRenovationNarrativeForm


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
        widget=forms.NumberInput(attrs={"placeholder": "Enter amount", "inputmode": "decimal"}),
    )
    has_prior_gclba_purchase = forms.ChoiceField(
        choices=[("no", "No"), ("yes", "Yes")],
        widget=forms.RadioSelect,
        initial="no",
        label="Have you previously purchased property from GCLBA?",
        help_text="If yes, you will need to provide proof of investment in your prior purchase.",
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


R4RRenovationNarrativeForm = BaseRenovationNarrativeForm


# R4R acknowledgments are identical to Featured Homes (same 6 fields, same labels).
R4RAcknowledgmentsForm = FHAcknowledgmentsForm
