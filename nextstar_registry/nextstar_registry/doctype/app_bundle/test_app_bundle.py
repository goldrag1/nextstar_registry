import frappe
from frappe.tests import IntegrationTestCase


class TestAppBundle(IntegrationTestCase):
    def setUp(self):
        # Ensure a test app exists in Registry App
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

    def test_bundle_with_valid_apps(self):
        bundle = frappe.get_doc({
            "doctype": "App Bundle",
            "bundle_name": "test-bundle",
            "title": "Test Bundle",
            "apps": [{"app": "test-app", "install_order": 1, "required": 1}],
        })
        bundle.insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("App Bundle", "test-bundle"))
        bundle.delete(ignore_permissions=True)

    def test_bundle_with_invalid_app_fails(self):
        bundle = frappe.get_doc({
            "doctype": "App Bundle",
            "bundle_name": "bad-bundle",
            "title": "Bad Bundle",
            "apps": [{"app": "nonexistent-app", "install_order": 1, "required": 1}],
        })
        self.assertRaises(frappe.ValidationError, bundle.insert, ignore_permissions=True)
