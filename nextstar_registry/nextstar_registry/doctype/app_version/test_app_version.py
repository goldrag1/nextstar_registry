import frappe
from frappe.tests import IntegrationTestCase


class TestAppVersion(IntegrationTestCase):
    def setUp(self):
        if not frappe.db.exists("Registry Developer", "test@test.com"):
            frappe.get_doc({
                "doctype": "Registry Developer",
                "developer_name": "Test Dev",
                "email": "test@test.com",
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("Registry App", "test-app"):
            frappe.get_doc({
                "doctype": "Registry App",
                "app_name": "test-app",
                "title": "Test App",
                "developer": "test@test.com",
                "github_url": "https://github.com/test/test-app",
            }).insert(ignore_permissions=True)

    def test_create_version(self):
        name = "test-app-1.0.0"
        if frappe.db.exists("App Version", name):
            frappe.delete_doc("App Version", name, force=True)

        doc = frappe.get_doc({
            "doctype": "App Version",
            "app": "test-app",
            "version": "1.0.0",
            "release_notes": "Initial release",
            "release_date": "2026-03-23",
        })
        doc.insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("App Version", name))
        doc.delete(ignore_permissions=True)
