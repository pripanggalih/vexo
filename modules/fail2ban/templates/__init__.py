"""Jail templates for fail2ban module."""

from .web_apps import WEB_APP_TEMPLATES
from .web_security import WEB_SECURITY_TEMPLATES

# All available templates
ALL_TEMPLATES = {
    **WEB_APP_TEMPLATES,
    **WEB_SECURITY_TEMPLATES,
}


def get_template(name):
    """Get a template by name."""
    return ALL_TEMPLATES.get(name)


def get_templates_by_category():
    """Get templates organized by category."""
    return {
        "Web Applications": WEB_APP_TEMPLATES,
        "Web Security": WEB_SECURITY_TEMPLATES,
    }


def list_templates():
    """List all available templates with descriptions."""
    templates = []
    for name, template in ALL_TEMPLATES.items():
        templates.append({
            "name": name,
            "display_name": template.get("display_name", name),
            "description": template.get("description", ""),
            "category": template.get("category", "Other"),
        })
    return templates
