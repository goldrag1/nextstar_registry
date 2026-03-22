import json

import frappe
from frappe.model.document import Document


class AppSubmission(Document):
    def on_update(self):
        if self.has_value_changed("status") and self.status == "Approved":
            self._create_or_update_registry_app()

    def _create_or_update_registry_app(self):
        if frappe.db.exists("Registry App", self.app_name):
            app = frappe.get_doc("Registry App", self.app_name)
            app.latest_version = self.version
            app.github_url = self.github_url
            if self.description:
                app.description = self.description
            if self.category:
                app.category = self.category
            app.save(ignore_permissions=True)
        else:
            app = frappe.get_doc({
                "doctype": "Registry App",
                "app_name": self.app_name,
                "title": self.app_name.replace("_", " ").title(),
                "description": self.description or "",
                "category": self.category or "",
                "developer": self.developer,
                "trust_tier": "Community",
                "license_type": self.license_type or "Open Source",
                "license": self.license or "",
                "github_url": self.github_url,
                "latest_version": self.version,
                "status": "Active",
            })
            app.insert(ignore_permissions=True)

        self.reviewed_at = frappe.utils.now_datetime()
        frappe.db.commit()
