"""
Shared forms used across all four program paths.

Steps 1-3 are identical regardless of program:
  Step 1: IdentityForm — applicant contact info
  Step 2: PropertyForm — property + program selection
  Step 3: EligibilityForm — hard disqualifier gate
"""

from django import forms
from django.core.validators import RegexValidator

from ..models import Application

# Accepts: (810) 555-0123, 810-555-0123, 810.555.0123, 8105550123, +1 810-555-0123
_phone_validator = RegexValidator(
    regex=r"^\+?1?\s*[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    message="Enter a valid phone number, e.g. (810) 555-0123",
)


class IdentityForm(forms.Form):
    """Step 1: Applicant Identity — name, contact, mailing address."""

    first_name = forms.CharField(max_length=100, label="First Name")
    last_name = forms.CharField(max_length=100, label="Last Name")
    email = forms.EmailField(label="Email Address")
    phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        validators=[_phone_validator],
    )
    preferred_contact = forms.ChoiceField(
        choices=Application.PreferredContact.choices,
        initial=Application.PreferredContact.EMAIL,
        label="Preferred Contact Method",
    )
    mailing_address = forms.CharField(max_length=255, label="Mailing Address")
    city = forms.CharField(max_length=100, label="City")
    state = forms.ChoiceField(
        choices=[
            ("AL", "AL"), ("AK", "AK"), ("AZ", "AZ"), ("AR", "AR"), ("CA", "CA"),
            ("CO", "CO"), ("CT", "CT"), ("DE", "DE"), ("FL", "FL"), ("GA", "GA"),
            ("HI", "HI"), ("ID", "ID"), ("IL", "IL"), ("IN", "IN"), ("IA", "IA"),
            ("KS", "KS"), ("KY", "KY"), ("LA", "LA"), ("ME", "ME"), ("MD", "MD"),
            ("MA", "MA"), ("MI", "MI"), ("MN", "MN"), ("MS", "MS"), ("MO", "MO"),
            ("MT", "MT"), ("NE", "NE"), ("NV", "NV"), ("NH", "NH"), ("NJ", "NJ"),
            ("NM", "NM"), ("NY", "NY"), ("NC", "NC"), ("ND", "ND"), ("OH", "OH"),
            ("OK", "OK"), ("OR", "OR"), ("PA", "PA"), ("RI", "RI"), ("SC", "SC"),
            ("SD", "SD"), ("TN", "TN"), ("TX", "TX"), ("UT", "UT"), ("VT", "VT"),
            ("VA", "VA"), ("WA", "WA"), ("WV", "WV"), ("WI", "WI"), ("WY", "WY"),
            ("DC", "DC"),
        ],
        initial="MI",
        label="State",
    )
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
