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


def expire_featured_listings():
    """Expire featured listings past their end date."""
    from frappe.utils import today
    frappe.db.sql(
        """UPDATE `tabFeatured Listing` SET status='Expired'
        WHERE status='Active' AND end_date < %s""", today()
    )
    frappe.db.commit()


def cleanup_old_health_reports():
    """Daily: delete health reports older than 90 days."""
    frappe.db.sql(
        """DELETE FROM `tabHealth Report`
        WHERE report_date < DATE_SUB(CURDATE(), INTERVAL 90 DAY) LIMIT 1000"""
    )
    frappe.db.commit()


def check_app_integrity():
    """Daily: compare stored commit hash vs GitHub HEAD for active apps."""
    from nextstar_registry.nextstar_registry.scanner_proxy import _get_github_head_hash

    apps = frappe.get_all(
        "Registry App",
        filters={
            "status": "Active",
            "github_url": ("!=", ""),
            "approved_commit_hash": ("!=", ""),
        },
        fields=["app_name", "github_url", "approved_commit_hash"],
    )

    for app in apps:
        current_hash = _get_github_head_hash(app["github_url"])
        if current_hash and current_hash != app["approved_commit_hash"]:
            frappe.db.set_value("Registry App", app["app_name"], {
                "integrity_status": "Flagged",
                "integrity_last_checked": frappe.utils.now_datetime(),
            })
        else:
            frappe.db.set_value("Registry App", app["app_name"], {
                "integrity_status": "Clean" if current_hash else "Unknown",
                "integrity_last_checked": frappe.utils.now_datetime(),
            })
    frappe.db.commit()


def poll_batch_scan_results():
    """Hourly: check pending batch scans for results."""
    settings = frappe.get_single("Registry Settings")
    api_key = settings.get_password("anthropic_api_key") if settings.anthropic_api_key else None
    if not api_key:
        return

    # Find submissions with pending batch scans
    submissions = frappe.get_all(
        "App Submission",
        filters={"scan_result": ("like", "%batch_id%")},
        fields=["name", "scan_result", "developer"],
    )

    from nextstar_registry.nextstar_registry.ai_scanner import check_batch_result

    for sub in submissions:
        try:
            scan_data = json.loads(sub["scan_result"])
            if scan_data.get("status") != "processing":
                continue

            batch_id = scan_data.get("batch_id")
            if not batch_id:
                continue

            results = check_batch_result(batch_id, api_key)
            if results is None:
                continue  # Still processing

            # Merge batch AI results with existing lint results
            lint_data = scan_data.get("lint", {})
            lint_findings = lint_data.get("findings", [])
            ai_findings = results[0].get("findings", []) if results else []

            combined = {
                "findings": lint_findings + ai_findings,
                "summary": f"Lint: {len(lint_findings)} findings, AI: {len(ai_findings)} findings",
                "scan_type": "combined",
                "ai_ran": True,
            }

            submission = frappe.get_doc("App Submission", sub["name"])
            submission.scan_result = json.dumps(combined)
            submission.ai_scan_ran = 1
            submission.save(ignore_permissions=True)
            frappe.db.commit()

            # Notify developer
            from nextstar_registry.nextstar_registry.scanner_proxy import _notify_scan_complete
            _notify_scan_complete(submission, combined)

        except Exception as e:
            frappe.log_error(title=f"Batch scan poll error: {sub['name']}", message=str(e))


def calculate_monthly_payouts():
    """Monthly: calculate payouts for all developers with sales."""
    from frappe.utils import add_months, getdate, today

    period_end = getdate(today())
    period_start = add_months(period_end, -1)

    settings = frappe.get_single("Registry Settings")
    commission_rate = float(settings.commission_rate or 15) / 100

    # Get all licenses issued in the period
    licenses = frappe.get_all(
        "App License",
        filters={
            "issued_at": ("between", [period_start, period_end]),
            "stripe_payment_id": ("!=", ""),
        },
        fields=["app", "buyer_email", "stripe_payment_id", "issued_at"],
    )

    # Group by developer
    dev_sales = {}
    for lic in licenses:
        app = frappe.get_doc("Registry App", lic["app"])
        developer = app.developer
        if not developer:
            continue
        if developer not in dev_sales:
            dev_sales[developer] = {"total": 0, "items": []}
        price = float(app.price or 0)
        dev_sales[developer]["total"] += price
        dev_sales[developer]["items"].append({
            "app": lic["app"], "price": price, "date": str(lic["issued_at"]),
        })

    # Create payout records
    for developer, data in dev_sales.items():
        commission = data["total"] * commission_rate
        net = data["total"] - commission
        frappe.get_doc({
            "doctype": "Developer Payout",
            "developer": developer,
            "period_start": period_start,
            "period_end": period_end,
            "total_sales": data["total"],
            "commission_amount": commission,
            "net_payout": net,
            "line_items": json.dumps(data["items"]),
        }).insert(ignore_permissions=True)

    frappe.db.commit()
