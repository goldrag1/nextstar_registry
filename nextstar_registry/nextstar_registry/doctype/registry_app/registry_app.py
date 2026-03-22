import re

import frappe
from frappe.model.document import Document

GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[\w.\-]+/[\w.\-]+(\.git)?$")


class RegistryApp(Document):
    def validate(self):
        if self.github_url and not GITHUB_URL_PATTERN.match(self.github_url):
            frappe.throw("Invalid GitHub URL format")

    def after_insert(self):
        if self.developer:
            dev = frappe.get_doc("Registry Developer", self.developer)
            dev.total_apps = frappe.db.count("Registry App", {"developer": self.developer})
            dev.save(ignore_permissions=True)
