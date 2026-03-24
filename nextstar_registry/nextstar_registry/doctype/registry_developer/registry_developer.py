import frappe
from frappe.model.document import Document
import secrets


class RegistryDeveloper(Document):
    def before_insert(self):
        if not self.api_key:
            self.api_key = secrets.token_hex(32)
            self.api_key_created = frappe.utils.now_datetime()

    def regenerate_key(self):
        """Generate a new API key, invalidating the old one."""
        self.api_key = frappe.generate_hash(length=64)
        self.api_key_created = frappe.utils.now_datetime()
        self.api_key_usage_count = 0
        self.save(ignore_permissions=True)
        return self.api_key
