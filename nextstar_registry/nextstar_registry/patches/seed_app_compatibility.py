import frappe


def execute():
    """Seed compatibility data for existing registry apps."""
    # hrms requires erpnext
    if frappe.db.exists("Registry App", "hrms"):
        frappe.db.set_value("Registry App", "hrms", {
            "required_apps": '["erpnext"]',
            "min_frappe_version": "15.0.0",
            "max_frappe_version": "16.99.99",
        })

    # All other apps: just Frappe version range
    for app in ["webshop", "helpdesk", "raven", "wiki"]:
        if frappe.db.exists("Registry App", app):
            frappe.db.set_value("Registry App", app, {
                "min_frappe_version": "15.0.0",
                "max_frappe_version": "16.99.99",
            })

    frappe.db.commit()
