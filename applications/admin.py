"""
Admin configuration for the applications app.

This gives the sales team a full management interface out of the box.
"""

from django.contrib import admin

from .models import Application, ApplicationNote, Document


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0


class ApplicationNoteInline(admin.StackedInline):
    model = ApplicationNote
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "property_interest",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "assigned_to", "created_at")
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
