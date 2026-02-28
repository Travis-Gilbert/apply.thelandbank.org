from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    name = "applications"

    def ready(self):
        # Django 6.0 compat patch for django-smartbase-admin 1.1.1
        # SmartBase's ColorSchemeForm.__init__ calls format_html(f'...')
        # without substitution args, which raises TypeError in Django 6.0.
        # Replace the module-level format_html with mark_safe until SmartBase
        # ships a Django 6.0-compatible release.
        from django.utils.html import mark_safe

        import django_smartbase_admin.views.user_config_view as ucv

        ucv.format_html = mark_safe
