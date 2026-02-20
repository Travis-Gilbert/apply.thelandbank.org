"""
URL patterns for the buyer-facing application form.
"""

from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    # Multi-step form
    path("", views.apply_start, name="step1"),
    path("step2/", views.step2_property, name="step2"),
    path("step3/", views.step3_offer, name="step3"),
    path("step4/", views.step4_eligibility, name="step4"),
    path("step5/", views.step5_documents, name="step5"),
    path("step6/", views.step6_rehab, name="step6"),
    path("step7/", views.step7_land_contract, name="step7"),
    path("step8/", views.step8_acknowledgments, name="step8"),
    # Save & resume
    path("save/", views.save_progress, name="save_progress"),
    path("resume/<uuid:token>/", views.resume_draft, name="resume"),
]
