"""
Shared forms used across all four program paths.

  Step 1: PropertySearchForm - address autocomplete + auto-program routing
  Step 2: IdentityForm - applicant contact info
  Step 3: EligibilityForm - hard disqualifier gate

Legacy PropertyForm kept for reference but no longer used in the accordion.
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
    """Step 1: Applicant Identity - name, contact, mailing address."""

    first_name = forms.CharField(
        max_length=100, label="First Name",
        widget=forms.TextInput(attrs={"placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=100, label="Last Name",
        widget=forms.TextInput(attrs={"placeholder": "Last name"}),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )
    phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        validators=[_phone_validator],
        widget=forms.TextInput(attrs={"placeholder": "(810) 555-0123", "inputmode": "tel"}),
    )
    preferred_contact = forms.ChoiceField(
        choices=Application.PreferredContact.choices,
        initial=Application.PreferredContact.EMAIL,
        label="Preferred Contact Method",
    )
    mailing_address = forms.CharField(
        max_length=255, label="Mailing Address",
        widget=forms.TextInput(attrs={"placeholder": "123 Main St"}),
    )
    city = forms.CharField(
        max_length=100, label="City",
        widget=forms.TextInput(attrs={"placeholder": "City"}),
    )
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
    zip_code = forms.CharField(
        max_length=10, label="ZIP Code",
        widget=forms.TextInput(attrs={"placeholder": "ZIP code", "inputmode": "numeric"}),
    )
    purchasing_entity_name = forms.CharField(
        max_length=200,
        required=False,
        label="Purchasing Entity Name",
        help_text="If purchasing through an LLC, trust, or other entity",
        widget=forms.TextInput(attrs={"placeholder": "LLC or entity name (if applicable)"}),
    )
    contact_name_different = forms.CharField(
        max_length=200,
        required=False,
        label="Alternate Contact Name",
        help_text="If the primary contact is different from the buyer",
        widget=forms.TextInput(attrs={"placeholder": "Contact name (if different from buyer)"}),
    )


class PropertyForm(forms.Form):
    """Step 2: Property Information - address, parcel, program selection."""

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


class PropertySearchForm(forms.Form):
    """
    Step 1: Find Your Property - address autocomplete + program auto-routing.

    Buyer types an address → HTMX autocomplete → selects a property → program
    auto-fills from the Property model.  If the property isn't in the database,
    the buyer picks a program manually via fallback cards.
    """

    property_address = forms.CharField(max_length=255, label="Property Address")
    parcel_id = forms.CharField(max_length=50, required=False, label="Parcel ID")
    property_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    program_type = forms.ChoiceField(
        choices=Application.ProgramType.choices,
        required=False,
        widget=forms.HiddenInput,
    )
    attended_open_house = forms.BooleanField(
        required=False,
        label="I have attended an open house or visited this property",
    )
    open_house_date = forms.CharField(
        required=False,
        max_length=7,
        label="Date of visit (if applicable)",
        help_text="Month and year is fine",
    )

    def clean(self):
        cleaned = super().clean()
        property_id = cleaned.get("property_id")
        program_type = cleaned.get("program_type")

        if property_id:
            from ..models import Property

            try:
                prop = Property.objects.get(id=property_id, status="available")
                # Property is the authoritative source for program + parcel
                cleaned["program_type"] = prop.program_type
                cleaned["parcel_id"] = prop.parcel_id
                cleaned["property_address"] = prop.address
            except Property.DoesNotExist:
                raise forms.ValidationError(
                    "This property is no longer available. Please select another."
                )
        elif not program_type:
            raise forms.ValidationError(
                "Please select a property from the suggestions, "
                "or choose a program manually."
            )

        return cleaned


class EligibilityForm(forms.Form):
    """
    Step 3: Eligibility gate - hard disqualifiers.

    If either answer is "Yes", the buyer is blocked from continuing.
    Uses Yes/No radio buttons (not checkboxes) because the question
    framing asks "Do you owe..." - a checkbox default of unchecked
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
