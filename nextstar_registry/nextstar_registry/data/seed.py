import json

import frappe

SEED_APPS = [
    {"app_name": "hrms", "title": "HRMS", "description": "Human Resources & Payroll management with attendance, leaves, expense claims, and salary processing.", "category": "HR & Payroll", "trust_tier": "Verified", "latest_version": "16.5.2", "github_url": "https://github.com/frappe/hrms", "license": "GPL-3.0", "frappe_compat": ["v15", "v16"], "rating": 4.8, "install_count": 12000, "safety_labels": {"doctypes_modified": 0, "custom_fields": 0, "scheduler_jobs": 3, "external_apis": False}},
    {"app_name": "webshop", "title": "Webshop", "description": "E-Commerce integration for ERPNext with product catalog, cart, and checkout.", "category": "E-Commerce", "trust_tier": "Verified", "latest_version": "16.2.0", "github_url": "https://github.com/frappe/webshop", "license": "GPL-3.0", "frappe_compat": ["v15", "v16"], "rating": 4.3, "install_count": 5600, "safety_labels": {"doctypes_modified": 2, "custom_fields": 5, "scheduler_jobs": 1, "external_apis": False}},
    {"app_name": "helpdesk", "title": "Helpdesk", "description": "Customer support and ticketing system with SLA management and knowledge base.", "category": "Support", "trust_tier": "Verified", "latest_version": "1.3.0", "github_url": "https://github.com/frappe/helpdesk", "license": "AGPL-3.0", "frappe_compat": ["v15", "v16"], "rating": 4.1, "install_count": 3200, "safety_labels": {"doctypes_modified": 0, "custom_fields": 0, "scheduler_jobs": 2, "external_apis": False}},
    {"app_name": "raven", "title": "Raven", "description": "Team messaging and collaboration built into Frappe. Channels, DMs, threads.", "category": "Communication", "trust_tier": "Verified", "latest_version": "2.1.0", "github_url": "https://github.com/The-Commit-Company/raven", "license": "AGPL-3.0", "frappe_compat": ["v15", "v16"], "rating": 4.6, "install_count": 4500, "safety_labels": {"doctypes_modified": 0, "custom_fields": 0, "scheduler_jobs": 1, "external_apis": False}},
    {"app_name": "wiki", "title": "Wiki", "description": "Simple wiki for your Frappe site. Markdown support, version history.", "category": "Utilities", "trust_tier": "Verified", "latest_version": "2.0.0", "github_url": "https://github.com/frappe/wiki", "license": "MIT", "frappe_compat": ["v14", "v15", "v16"], "rating": 4.2, "install_count": 2800, "safety_labels": {"doctypes_modified": 0, "custom_fields": 0, "scheduler_jobs": 0, "external_apis": False}},
]


def run():
    """Seed registry with initial app data."""
    # Create a default developer for Frappe Technologies
    dev_email = "hello@frappe.io"
    if not frappe.db.exists("Registry Developer", dev_email):
        frappe.get_doc({
            "doctype": "Registry Developer",
            "developer_name": "Frappe Technologies",
            "email": dev_email,
            "github_username": "frappe",
            "website": "https://frappe.io",
            "verified": 1,
            "verified_date": frappe.utils.now_datetime(),
        }).insert(ignore_permissions=True)

    for data in SEED_APPS:
        if frappe.db.exists("Registry App", data["app_name"]):
            continue
        app = frappe.get_doc({
            "doctype": "Registry App",
            "developer": dev_email,
            "license_type": "Open Source",
            "status": "Active",
            **{k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in data.items()},
        })
        app.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"Seeded {len(SEED_APPS)} apps")
