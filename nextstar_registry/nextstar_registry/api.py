import frappe


@frappe.whitelist(allow_guest=True)
def get_catalog(category=None, search=None, trust_tier=None, page=1, page_size=20):
    """Public catalog endpoint for the App Store client."""
    filters = {"status": "Active"}
    if category:
        filters["category"] = category
    if trust_tier:
        filters["trust_tier"] = trust_tier

    or_filters = None
    if search:
        or_filters = [
            ["app_name", "like", f"%{search}%"],
            ["title", "like", f"%{search}%"],
            ["description", "like", f"%{search}%"],
        ]

    page = int(page)
    page_size = min(int(page_size), 100)
    start = (page - 1) * page_size

    apps = frappe.get_all(
        "Registry App",
        filters=filters,
        or_filters=or_filters,
        fields=["app_name", "title", "description", "category", "developer",
                "trust_tier", "license_type", "license", "github_url",
                "latest_version", "frappe_compat", "icon_url", "rating",
                "install_count", "safety_labels", "status"],
        order_by="install_count desc",
        start=start,
        page_length=page_size,
    )

    # Parse JSON fields
    for app in apps:
        for field in ("frappe_compat", "safety_labels"):
            if app.get(field) and isinstance(app[field], str):
                try:
                    app[field] = frappe.parse_json(app[field])
                except Exception:
                    pass
        # Add developer name
        if app.get("developer"):
            app["developer_name"] = frappe.db.get_value(
                "Registry Developer", app["developer"], "developer_name"
            ) or app["developer"]

    return apps


@frappe.whitelist(allow_guest=True)
def get_app_detail(app_name):
    """Get full detail for a single app."""
    if not frappe.db.exists("Registry App", app_name):
        frappe.throw(f"App '{app_name}' not found", frappe.DoesNotExistError)

    app = frappe.get_doc("Registry App", app_name).as_dict()

    for field in ("frappe_compat", "safety_labels"):
        if app.get(field) and isinstance(app[field], str):
            try:
                app[field] = frappe.parse_json(app[field])
            except Exception:
                pass

    if app.get("developer"):
        dev = frappe.get_doc("Registry Developer", app["developer"])
        app["developer_name"] = dev.developer_name
        app["developer_url"] = dev.website or ""

    return app


@frappe.whitelist(allow_guest=True)
def get_categories():
    """Get unique active categories."""
    cats = frappe.get_all(
        "Registry App",
        filters={"status": "Active"},
        fields=["category"],
        distinct=True,
    )
    return sorted([c["category"] for c in cats if c.get("category")])


@frappe.whitelist(allow_guest=True)
def search_apps(query):
    """Search apps by name, title, or description."""
    if not query or len(query) < 2:
        return []
    return get_catalog(search=query)


@frappe.whitelist()
def register_developer(developer_name, email, github_username=None):
    """Register a new developer. Returns API key."""
    if frappe.db.exists("Registry Developer", email):
        frappe.throw(f"Developer with email '{email}' already exists")

    dev = frappe.get_doc({
        "doctype": "Registry Developer",
        "developer_name": developer_name,
        "email": email,
        "github_username": github_username or "",
    })
    dev.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"email": dev.email, "api_key": dev.api_key, "developer_name": dev.developer_name}


@frappe.whitelist()
def submit_app(app_name, github_url, version, description=None, category=None,
               license_type="Open Source", license=None, developer_email=None):
    """Submit an app for review."""
    if not developer_email:
        developer_email = frappe.session.user

    if not frappe.db.exists("Registry Developer", developer_email):
        frappe.throw("You must register as a developer first")

    submission = frappe.get_doc({
        "doctype": "App Submission",
        "developer": developer_email,
        "app_name": app_name,
        "github_url": github_url,
        "version": version,
        "description": description or "",
        "category": category or "",
        "license_type": license_type,
        "license": license or "",
    })
    submission.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"submission": submission.name, "status": submission.status}


@frappe.whitelist(allow_guest=True)
def report_install(app_name):
    """Anonymous install counter - increment install_count."""
    if frappe.db.exists("Registry App", app_name):
        frappe.db.set_value("Registry App", app_name, "install_count",
                           frappe.db.get_value("Registry App", app_name, "install_count") + 1)
        frappe.db.commit()
    return {"status": "ok"}
