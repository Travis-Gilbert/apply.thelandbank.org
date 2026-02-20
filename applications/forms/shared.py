"""
Shared forms used across all four program paths.

Steps 1-3 are identical regardless of program:
  Step 1: IdentityForm — applicant contact info
  Step 2: PropertyForm — property + program selection
  Step 3: EligibilityForm — hard disqualifier gate
"""

from django import forms

from ..models import Application


class IdentityForm(forms.Form):
    """Step 1: Applicant Identity — name, contact, mailing address."""

    first_name = forms.CharField(max_length=100, label="First Name")
    last_name = forms.CharField(max_length=100, label="Last Name")
    email = forms.EmailField(label="Email Address")
    phone = forms.CharField(max_length=20, label="Phone Number")
    preferred_contact = forms.ChoiceField(
        choices=Application.PreferredContact.choices,
        initial=Application.PreferredContact.EMAIL,
        label="Preferred Contact Method",
    )
    mailing_address = forms.CharField(max_length=255, label="Mailing Address")
    city = forms.CharField(max_length=100, label="City")
    state = forms.CharField(max_length=2, initial="MI", label="State")
    zip_code = forms.CharField(max_length=10, label="ZIP Code")
    purchasing_entity_name = forms.CharField(
        max_length=200,
        required=False,
        label="Purchasing Entity Name",
        help_text="If purchasing through an LLC, trust, or other entity",
    )
    contact_name_different = forms.CharField(
        max_length=200,
        required=False,
        label="Alternate Contact Name",
        help_text="If the primary contact is different from the buyer",
    )


class PropertyForm(forms.Form):
    """Step 2: Property Information — address, parcel, program selection."""

    property_address = forms.CharField(max_length=255, label="Property Address")
    parcel_id = forms.CharField(
        max_length=50,
        required=False,
        label="Parcel ID (if known)",
    )
    program_type = forms.ChoiceField(
        choices=Application.ProgramType.choices,
        widget=forms.RadioSelect,
        label="Which program are you applying for?",
    )
    attended_open_house = forms.BooleanField(
        required=False,
        label="I have attended an open house or visited this property",
    )
    open_house_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date of visit (if applicable)",
    )


class EligibilityForm(forms.Form):
    """
    Step 3: Eligibility gate — hard disqualifiers.

    If either answer is "Yes", the buyer is blocked from continuing.
    Uses Yes/No radio buttons (not checkboxes) because the question
    framing asks "Do you owe..." — a checkbox default of unchecked
    would be ambiguous.
    """

    has_delinquent_taxes = forms.ChoiceField(
        choices=[("no", "No"), ("yes", "Yes")],
        widget=forms.RadioSelect,
        label="Do you currently owe delinquent property taxes in Genesee County?",
    )
    has_tax_foreclosure = forms.ChoiceField(
        choices=[("no", "No"), ("yes", "Yes")],
        widget=forms.RadioSelect,
        label=(
            "Have you lost property to tax foreclosure with the Genesee County "
            "Treasurer in the last five years?"
        ),
    )
