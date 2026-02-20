"""
Admin configuration for the applications app.

Uses Django Unfold for a modern admin interface for the sales team.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display

from .models import Application, ApplicationNote, Document


class DocumentInline(TabularInline):
    model = Document
    extra = 0
    hide_title = True


class ApplicationNoteInline(StackedInline):
    model = ApplicationNote
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "property_interest",
        "display_status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "assigned_to", "created_at")
    list_filter_submit = True
    search_fields = ("first_name", "last_name", "email", "property_interest")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DocumentInline, ApplicationNoteInline]

    fieldsets = (
        ("Applicant", {
            "fields": ("first_name", "last_name", "email", "phone"),
        }),
        ("Address", {
            "fields": ("street_address", "city", "state", "zip_code"),
        }),
        ("Application", {
            "fields": ("property_interest", "notes"),
        }),
        ("Workflow", {
            "fields": ("status", "assigned_to", "submitted_at"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @display(
        description="Status",
        label={
            Application.Status.DRAFT: "info",
            Application.Status.SUBMITTED: "warning",
            Application.Status.UNDER_REVIEW: "warning",
            Application.Status.APPROVED: "success",
            Application.Status.DENIED: "danger",
            Application.Status.WITHDRAWN: "info",
        },
    )
    def display_status(self, instance):
        return instance.status
