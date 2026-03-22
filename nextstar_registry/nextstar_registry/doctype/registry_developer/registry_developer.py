import frappe
from frappe.model.document import Document
import secrets


class RegistryDeveloper(Document):
    def before_insert(self):
        if not self.api_key:
            self.api_key = secrets.token_hex(32)
