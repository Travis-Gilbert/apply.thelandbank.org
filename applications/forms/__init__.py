"""
Forms package for the GCLBA multi-step application process.

Re-exports all form classes so consumers can do:
    from applications.forms import IdentityForm, FHOfferForm, ...
"""

from .featured_homes import (
    FHAcknowledgmentsForm,
    FHHomebuyerEdForm,
    FHOfferForm,
    FHRenovationNarrativeForm,
)
from .ready_for_rehab import (
    R4RAcknowledgmentsForm,
    R4RLineItemsForm,
    R4ROfferForm,
    R4RRenovationNarrativeForm,
)
from .shared import EligibilityForm, IdentityForm, PropertyForm, PropertySearchForm
from .vip_spotlight import VIPAcknowledgmentsForm, VIPProposalForm

__all__ = [
    # Shared
    "IdentityForm",
    "PropertyForm",
    "PropertySearchForm",
    "EligibilityForm",
    # Featured Homes
    "FHOfferForm",
    "FHRenovationNarrativeForm",
    "FHHomebuyerEdForm",
    "FHAcknowledgmentsForm",
    # Ready for Rehab
    "R4ROfferForm",
    "R4RLineItemsForm",
    "R4RRenovationNarrativeForm",
    "R4RAcknowledgmentsForm",
    # VIP Spotlight
    "VIPProposalForm",
    "VIPAcknowledgmentsForm",
]
