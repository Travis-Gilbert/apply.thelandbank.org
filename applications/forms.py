"""
Forms for the GCLBA multi-step application process.

Each form corresponds to one step in the buyer flow. Data is stored
in ApplicationDraft.form_data (JSONField) between steps, then hydrated
into a flat Application model on final submission.
"""

from django import forms

from .models import Application


class Step1IdentityForm(forms.Form):
    """Section 1: Applicant Identity — name, contact, address."""

    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    preferred_contact = forms.ChoiceField(
        choices=Application.PreferredContact.choices,
        initial=Application.PreferredContact.EMAIL,
    )
    street_address = forms.CharField(max_length=255)
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=2, initial="MI")
    zip_code = forms.CharField(max_length=10)


class Step2PropertyForm(forms.Form):
    """Section 2: Property Information — address, parcel, program type."""

    property_address = forms.CharField(max_length=255, label="Property Address")
    parcel_id = forms.CharField(max_length=50, required=False, label="Parcel ID (if known)")
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


class Step3OfferForm(forms.Form):
    """Section 3: Offer Details — amount, purchase type, intended use."""

    offer_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="Offer Amount ($)",
    )
    purchase_type = forms.ChoiceField(
        choices=Application.PurchaseType.choices,
        widget=forms.RadioSelect,
        label="How will you finance this purchase?",
    )
    intended_use = forms.ChoiceField(
        choices=Application.IntendedUse.choices,
        label="How do you plan to use this property?",
    )


class Step4EligibilityForm(forms.Form):
    """
    Section 4: Eligibility — hard disqualifiers.

    If either answer is "Yes", the buyer is blocked from continuing.
    """

    has_delinquent_taxes = forms.ChoiceField(
        choices=[("no", "No"), ("yes", "Yes")],
        widget=forms.RadioSelect,
        label="Do you currently owe delinquent property taxes in Genesee County?",
    )
    has_tax_foreclosure = forms.ChoiceField(
        choices=[("no", "No"), ("yes", "Yes")],
        widget=forms.RadioSelect,
        label="Have you ever lost property to tax foreclosure in Genesee County?",
    )


class Step6RehabForm(forms.Form):
    """Section 6: Rehab Plan — only shown for Ready for Rehab program."""

    rehab_scope = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Describe your planned rehabilitation work",
    )
    rehab_budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="Estimated Rehab Budget ($)",
    )
    rehab_timeline = forms.CharField(
        max_length=100,
        label="Expected completion timeline (e.g., '6 months')",
    )
    contractor_name = forms.CharField(
        max_length=200,
        required=False,
        label="Contractor Name (if selected)",
    )
    contractor_phone = forms.CharField(
        max_length=20,
        required=False,
        label="Contractor Phone",
    )


class Step7LandContractForm(forms.Form):
    """Section 7: Land Contract Details — only shown for land contract purchases."""

    lc_provider_name = forms.CharField(
        max_length=200,
        label="Land Contract Provider Name",
    )
    lc_provider_phone = forms.CharField(
        max_length=20,
        label="Provider Phone",
    )
    lc_term_months = forms.IntegerField(
        min_value=1,
        label="Contract Term (months)",
    )
    lc_interest_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        label="Interest Rate (%)",
    )


class Step8AcknowledgmentsForm(forms.Form):
    """Section 8: Acknowledgments — three required checkboxes."""

    ack_info_accurate = forms.BooleanField(
        label="I certify that all information provided in this application is true and accurate.",
    )
    ack_terms_conditions = forms.BooleanField(
        label=(
            "I agree to the GCLBA terms and conditions, including the requirement "
            "to close within 30 days of approval."
        ),
    )
    ack_inspection_waiver = forms.BooleanField(
        label=(
            "I understand that all properties are sold as-is and that I have had "
            "the opportunity to inspect the property."
        ),
    )
