import json

import frappe


def aggregate_health_data():
    """Daily: aggregate health reports into Registry App summary fields."""
    apps = frappe.get_all("Registry App", pluck="app_name")
    for app_name in apps:
        reports = frappe.db.sql("""
            SELECT COUNT(DISTINCT reporting_instance) as instances,
                   AVG(error_count) as avg_errors,
                   AVG(scheduler_success_rate) as avg_success
            FROM `tabHealth Report` WHERE app=%s AND report_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """, app_name, as_dict=True)
        if reports and reports[0].get("instances"):
            r = reports[0]
            # Get version distribution
            versions = frappe.db.sql("""
                SELECT frappe_version, COUNT(DISTINCT reporting_instance) as count
                FROM `tabHealth Report` WHERE app=%s AND report_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY frappe_version
            """, app_name, as_dict=True)
            version_dist = {v["frappe_version"]: v["count"] for v in versions if v.get("frappe_version")}
            frappe.db.set_value("Registry App", app_name, {
                "total_reporting_instances": r["instances"],
                "avg_error_rate": round(float(r["avg_errors"] or 0), 2),
                "avg_scheduler_success": round(float(r["avg_success"] or 0), 1),
                "frappe_version_distribution": json.dumps(version_dist),
            })
    frappe.db.commit()


def cleanup_old_health_reports():
    """Daily: delete health reports older than 90 days."""
    frappe.db.sql(
        """DELETE FROM `tabHealth Report`
        WHERE report_date < DATE_SUB(CURDATE(), INTERVAL 90 DAY) LIMIT 1000"""
    )
    frappe.db.commit()
