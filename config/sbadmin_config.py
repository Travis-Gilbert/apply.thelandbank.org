"""
SmartBase Admin configuration for GCLBA Application Portal.

Defines the sidebar menu structure and dashboard for staff users.
"""

from django_smartbase_admin.engine.configuration import (
    SBAdminConfigurationBase,
    SBAdminRoleConfiguration,
)
from django_smartbase_admin.models import ColorScheme
from django_smartbase_admin.engine.menu_item import SBAdminMenuItem
from django_smartbase_admin.views.dashboard_view import SBAdminDashboardView

from applications.admin_utils import DashboardStatsWidget


config = SBAdminRoleConfiguration(
    default_view=SBAdminMenuItem(view_id="dashboard"),
    menu_items=[
        SBAdminMenuItem(
            label="Dashboard",
            icon="All-application",
            view_id="dashboard",
        ),
        SBAdminMenuItem(
            label="Review Queue",
            icon="Checks",
            url="/admin/review/",
        ),
        SBAdminMenuItem(
            label="Applications",
            icon="Box",
            sub_items=[
                SBAdminMenuItem(
                    label="All Applications",
                    view_id="applications_application",
                ),
                SBAdminMenuItem(
                    label="In Progress",
                    view_id="applications_applicationdraft",
                ),
            ],
        ),
        SBAdminMenuItem(
            label="Properties",
            icon="Home",
            view_id="applications_property",
        ),
        SBAdminMenuItem(
            label="Users",
            icon="User-business",
            view_id="applications_user",
        ),
    ],
    registered_views=[
        SBAdminDashboardView(
            widgets=[DashboardStatsWidget()],
            title="GCLBA Application Portal",
        ),
    ],
)


class SBAdminConfiguration(SBAdminConfigurationBase):
    site_title = "GCLBA Sales Admin"
    site_header = "The Genesee County Land Bank Authority"
    default_color_scheme = ColorScheme.LIGHT

    def get_configuration_for_roles(self, user_roles):
        return config
