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


class BaseAcknowledgmentsForm(forms.Form):
    """
    Shared acknowledgments for all programs.

    Every program requires these four. Program-specific subclasses add their
    own fields (e.g. ack_highest_not_guaranteed for offer-based programs,
    ack_reconveyance_deed for VIP). Subclasses must set ``field_order`` to
    keep ack_info_accurate last, since templates iterate ``{% for field in form %}``.
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
    ack_info_accurate = forms.BooleanField(
        label="I certify that all information provided in this application is true and accurate.",
    )


class BaseRenovationNarrativeForm(forms.Form):
    """
    Shared renovation narrative for Featured Homes and Ready for Rehab.

    Intended use + conditional sub-question, then four open-ended questions
    about renovation plans, timeline, who performs the work, and funding.
    FH and R4R share identical fields and validation; both inherit directly.
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
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Describe the renovations you plan to make"}),
        label="What renovations will you be making?",
    )
    renovation_who = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Yourself, licensed contractor, etc."}),
        label="Who will complete the renovations?",
    )
    renovation_when = forms.CharField(
        max_length=200,
        label="When will renovations be completed?",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Within 12 months of closing"}),
    )
    renovation_funding = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Cash savings, construction loan, etc."}),
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
