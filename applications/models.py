"""
Models for the County Landing home sales application process.

This is a starting point -- we'll refine fields once specs come in from your boss.
For now, it covers the core of what a home buyer application typically needs.
"""

from django.db import models
from django.conf import settings


class Application(models.Model):
    """A home buyer's application to purchase a property."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        WITHDRAWN = "withdrawn", "Withdrawn"

    # Applicant info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    # Address
    street_address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, default="OH", blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # Application details
    property_interest = models.CharField(
        max_length=255,
        blank=True,
        help_text="Which property or lot the applicant is interested in",
    )
    notes = models.TextField(blank=True, help_text="Additional notes from the applicant")

    # Status and workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications",
        help_text="Sales team member handling this application",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_status_display()}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Document(models.Model):
    """Documents uploaded as part of an application (ID, proof of income, etc.)."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file = models.FileField(upload_to="applications/%Y/%m/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description or self.file.name} ({self.application})"


class ApplicationNote(models.Model):
    """Internal notes from the sales team on an application."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="team_notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.author} on {self.application}"
