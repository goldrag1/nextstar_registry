import frappe
from frappe.tests import IntegrationTestCase


class TestRegistryAPI(IntegrationTestCase):
    def setUp(self):
        # Create a test developer
        if not frappe.db.exists("Registry Developer", "test@dev.com"):
            frappe.get_doc({
                "doctype": "Registry Developer",
                "developer_name": "Test Dev",
                "email": "test@dev.com",
            }).insert(ignore_permissions=True)
        # Create a test app
        if not frappe.db.exists("Registry App", "test_api_app"):
            frappe.get_doc({
                "doctype": "Registry App",
                "app_name": "test_api_app",
                "title": "Test API App",
                "developer": "test@dev.com",
                "github_url": "https://github.com/test/app",
                "category": "Testing",
                "trust_tier": "Community",
                "status": "Active",
            }).insert(ignore_permissions=True)

    def test_get_catalog(self):
        from nextstar_registry.nextstar_registry.api import get_catalog
        result = get_catalog()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_catalog_search(self):
        from nextstar_registry.nextstar_registry.api import get_catalog
        result = get_catalog(search="test_api")
        self.assertGreater(len(result), 0)

    def test_get_app_detail(self):
        from nextstar_registry.nextstar_registry.api import get_app_detail
        result = get_app_detail("test_api_app")
        self.assertEqual(result["app_name"], "test_api_app")

    def test_get_categories(self):
        from nextstar_registry.nextstar_registry.api import get_categories
        result = get_categories()
        self.assertIn("Testing", result)

    def test_report_install(self):
        from nextstar_registry.nextstar_registry.api import report_install
        before = frappe.db.get_value("Registry App", "test_api_app", "install_count")
        report_install("test_api_app")
        after = frappe.db.get_value("Registry App", "test_api_app", "install_count")
        self.assertEqual(after, before + 1)

    def tearDown(self):
        frappe.db.rollback()
