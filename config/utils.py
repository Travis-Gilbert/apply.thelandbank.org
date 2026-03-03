"""
Utility functions for Django configuration.
"""

import os


def environment_callback(request):
    """
    Returns environment label for the admin header.
    Shows a colored badge so the sales team knows if they're
    in development vs production.
    """
    if os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes"):
        return "Development"
    return "Production"
