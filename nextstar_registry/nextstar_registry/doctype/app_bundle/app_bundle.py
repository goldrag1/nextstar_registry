import frappe
from frappe.model.document import Document


class AppBundle(Document):
    def validate(self):
        self._validate_apps_exist()

    def _validate_apps_exist(self):
        """Ensure all linked apps exist in Registry App."""
        for item in self.get("apps", []):
            if not frappe.db.exists("Registry App", item.app):
                frappe.throw(
                    f"App '{item.app}' does not exist in Registry App",
                    frappe.ValidationError,
                )
