import json

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
                "install_count", "safety_labels", "status",
                "pricing_type", "price", "currency",
                "demo_url", "demo_username", "demo_password", "demo_notes"],
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


@frappe.whitelist(allow_guest=True)
def get_bundles():
    """Get all available app bundles."""
    bundles = frappe.get_all(
        "App Bundle",
        fields=["bundle_name", "title", "description", "category", "icon", "install_count"],
    )
    for b in bundles:
        b["apps"] = frappe.get_all(
            "App Bundle Item",
            filters={"parent": b["bundle_name"]},
            fields=["app", "install_order", "required"],
            order_by="install_order asc",
        )
        # Add app titles
        for app in b["apps"]:
            app["title"] = frappe.db.get_value("Registry App", app["app"], "title") or app["app"]
    return bundles


@frappe.whitelist(allow_guest=True)
def get_bundle_detail(bundle_name):
    """Get bundle with its apps list."""
    if not frappe.db.exists("App Bundle", bundle_name):
        frappe.throw(f"Bundle '{bundle_name}' not found", frappe.DoesNotExistError)

    bundle = frappe.get_doc("App Bundle", bundle_name).as_dict()
    # Enrich apps with details
    for app_item in bundle.get("apps", []):
        app_doc = frappe.db.get_value(
            "Registry App", app_item.get("app"),
            ["title", "description", "github_url", "latest_version", "trust_tier"],
            as_dict=True,
        )
        if app_doc:
            app_item.update(app_doc)
    return bundle


# ---------------------------------------------------------------------------
# Task 1 — Content endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def get_app_versions(app_name, page=1, page_size=10):
    """Get version history for an app."""
    page = int(page)
    page_size = min(int(page_size), 50)
    start = (page - 1) * page_size
    return frappe.get_all(
        "App Version",
        filters={"app": app_name},
        fields=["version", "release_notes", "release_date", "frappe_compat"],
        order_by="release_date desc",
        start=start,
        page_length=page_size,
    )


@frappe.whitelist()
def submit_version(app_name, version, release_notes=None, frappe_compat=None):
    """Publish a new version."""
    if not frappe.db.exists("Registry App", app_name):
        frappe.throw(f"App '{app_name}' not found")
    doc = frappe.get_doc({
        "doctype": "App Version",
        "app": app_name,
        "version": version,
        "release_notes": release_notes or "",
        "release_date": frappe.utils.today(),
        "frappe_compat": frappe_compat or "[]",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.set_value("Registry App", app_name, "latest_version", version)
    frappe.db.commit()
    return {"version": doc.version, "name": doc.name}


@frappe.whitelist(allow_guest=True)
def get_screenshots(app_name):
    """Get screenshots for an app."""
    return frappe.get_all(
        "App Screenshot",
        filters={"app": app_name},
        fields=["image", "caption", "sort_order"],
        order_by="sort_order asc",
    )


@frappe.whitelist()
def upload_screenshot(app_name, caption=None):
    """Upload a screenshot for an app."""
    if not frappe.db.exists("Registry App", app_name):
        frappe.throw(f"App '{app_name}' not found")
    doc = frappe.get_doc({
        "doctype": "App Screenshot",
        "app": app_name,
        "caption": caption or "",
        "sort_order": frappe.db.count("App Screenshot", {"app": app_name}),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist(allow_guest=True)
def get_recent_updates(limit=5):
    """Get most recent app version releases across all apps."""
    limit = min(int(limit), 20)
    versions = frappe.get_all(
        "App Version",
        fields=["app", "version", "release_notes", "release_date"],
        order_by="release_date desc, creation desc",
        page_length=limit,
    )
    for v in versions:
        v["title"] = frappe.db.get_value("Registry App", v["app"], "title") or v["app"]
    return versions


# ---------------------------------------------------------------------------
# Task 2 — Trust endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def submit_review(app_name, rating, title, body=None, install_proof=None, nonce=None):
    """Submit a verified review."""
    if not frappe.db.exists("Registry App", app_name):
        frappe.throw(f"App '{app_name}' not found")
    rating = int(rating)
    if rating < 1 or rating > 5:
        frappe.throw("Rating must be between 1 and 5")

    # Validate nonce if provided (preferred over install_proof)
    if nonce:
        from nextstar_registry.nextstar_registry.review_nonce import validate_review_nonce

        if not validate_review_nonce(nonce, app_name):
            frappe.throw("Invalid or expired review nonce")
    elif install_proof and frappe.db.exists("App Review", {"install_proof": install_proof}):
        frappe.throw("Review already submitted with this install proof")

    doc = frappe.get_doc({
        "doctype": "App Review",
        "app": app_name,
        "rating": rating,
        "title": title,
        "body": body or "",
        "install_proof": install_proof or "",
        "reviewer_email": frappe.session.user,
        "status": "Published",
    })
    doc.insert(ignore_permissions=True)
    # Update average rating on Registry App
    avg = frappe.db.sql(
        """SELECT AVG(rating) FROM `tabApp Review`
        WHERE app=%s AND status='Published'""", app_name
    )[0][0] or 0
    frappe.db.set_value("Registry App", app_name, "rating", round(float(avg), 1))
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist(allow_guest=True)
def get_reviews(app_name, page=1, page_size=10):
    """Get reviews for an app."""
    page = int(page)
    page_size = min(int(page_size), 50)
    start = (page - 1) * page_size
    reviews = frappe.get_all(
        "App Review",
        filters={"app": app_name, "status": "Published"},
        fields=[
            "name", "reviewer_email", "rating", "title", "body", "helpful_count",
            "not_helpful_count", "developer_response", "developer_response_date", "creation",
        ],
        order_by="creation desc",
        start=start,
        page_length=page_size,
    )
    total = frappe.db.count("App Review", {"app": app_name, "status": "Published"})
    avg = frappe.db.sql(
        """SELECT AVG(rating) FROM `tabApp Review`
        WHERE app=%s AND status='Published'""", app_name
    )[0][0] or 0
    return {"reviews": reviews, "total": total, "average_rating": round(float(avg), 1)}


@frappe.whitelist()
def respond_to_review(review_name, response_text):
    """Developer responds to a review."""
    review = frappe.get_doc("App Review", review_name)
    review.developer_response = response_text
    review.developer_response_date = frappe.utils.now_datetime()
    review.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def vote_review(review_name, vote):
    """Vote a review helpful or not helpful."""
    if vote not in ("helpful", "not_helpful"):
        frappe.throw("Vote must be 'helpful' or 'not_helpful'")
    field = "helpful_count" if vote == "helpful" else "not_helpful_count"
    current = frappe.db.get_value("App Review", review_name, field) or 0
    frappe.db.set_value("App Review", review_name, field, current + 1)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def invite_reviewer(email, display_name):
    """Invite a community reviewer."""
    frappe.only_for("System Manager")
    if frappe.db.exists("Community Reviewer", email):
        frappe.throw(f"Reviewer '{email}' already exists")
    doc = frappe.get_doc({
        "doctype": "Community Reviewer",
        "email": email,
        "display_name": display_name,
        "status": "Invited",
        "invited_by": frappe.session.user,
        "invite_date": frappe.utils.today(),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"email": doc.email, "status": doc.status}


@frappe.whitelist()
def complete_review(submission_name, verdict, notes=None):
    """Community reviewer completes a submission review."""
    if verdict not in ("Approved", "Rejected"):
        frappe.throw("Verdict must be 'Approved' or 'Rejected'")
    submission = frappe.get_doc("App Submission", submission_name)
    submission.status = verdict
    submission.save(ignore_permissions=True)
    # Add reputation points to reviewer
    reviewer_email = frappe.session.user
    if frappe.db.exists("Community Reviewer", reviewer_email):
        reviewer = frappe.get_doc("Community Reviewer", reviewer_email)
        reviewer.reputation_points += 10
        reviewer.reviews_completed += 1
        reviewer.save(ignore_permissions=True)
    # Auto-upgrade developer trust level on first approval
    if verdict == "Approved" and submission.developer:
        if frappe.db.exists("Registry Developer", submission.developer):
            frappe.db.set_value("Registry Developer", submission.developer, "trust_level", "Established")
    frappe.db.commit()
    return {"status": verdict}


# ---------------------------------------------------------------------------
# Task 3 — Intelligence endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def report_health(instance_uuid, app_name, error_count, scheduler_success_rate, frappe_version):
    """Accept anonymous health report from an instance."""
    if not frappe.db.exists("Registry App", app_name):
        return {"status": "unknown_app"}
    doc = frappe.get_doc({
        "doctype": "Health Report",
        "app": app_name,
        "reporting_instance": instance_uuid,
        "error_count": int(error_count),
        "scheduler_success_rate": float(scheduler_success_rate),
        "frappe_version": frappe_version,
        "report_date": frappe.utils.today(),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def get_health_summary(app_name):
    """Get aggregate health for a developer's app."""
    if not frappe.db.exists("Registry App", app_name):
        frappe.throw(f"App '{app_name}' not found")
    app = frappe.get_doc("Registry App", app_name)
    return {
        "total_reporting_instances": app.total_reporting_instances or 0,
        "avg_error_rate": app.avg_error_rate or 0,
        "avg_scheduler_success": app.avg_scheduler_success or 0,
        "frappe_version_distribution": frappe.parse_json(app.frappe_version_distribution or "{}"),
    }


@frappe.whitelist(allow_guest=True)
def get_recommendations(installed_apps):
    """Get app recommendations based on installed apps."""
    if isinstance(installed_apps, str):
        installed_apps = json.loads(installed_apps)
    if not installed_apps:
        return []
    # Query using the denormalized child table
    placeholders = ", ".join(["%s"] * len(installed_apps))
    rule_names = frappe.db.sql(
        f"""SELECT DISTINCT parent FROM `tabRecommendation Rule App`
        WHERE app IN ({placeholders})""",
        tuple(installed_apps),
        as_list=True,
    )
    if not rule_names:
        return []
    rule_names = [r[0] for r in rule_names]
    recommendations = []
    for rule_name in rule_names:
        rule = frappe.get_doc("Recommendation Rule", rule_name)
        app_name = rule.then_recommend
        if app_name in installed_apps:
            continue  # Don't recommend already installed apps
        app_data = frappe.db.get_value(
            "Registry App", app_name,
            ["app_name", "title", "description", "category", "trust_tier", "rating",
             "install_count", "github_url", "latest_version", "icon_url"],
            as_dict=True,
        )
        if app_data:
            app_data["recommendation_reason"] = rule.category
            app_data["priority"] = rule.priority
            recommendations.append(app_data)
    recommendations.sort(key=lambda x: x.get("priority", 0), reverse=True)
    return recommendations


@frappe.whitelist(allow_guest=True)
def get_featured():
    """Get featured apps for the Today tab (includes Featured Listing entries)."""
    featured = frappe.get_all(
        "Registry App",
        filters={"featured": 1, "status": "Active"},
        fields=[
            "app_name", "title", "description", "category", "developer",
            "trust_tier", "rating", "install_count", "github_url", "latest_version", "icon_url",
            "price", "pricing_type",
        ],
    )
    featured_app_names = {a["app_name"] for a in featured}

    # Merge active Featured Listings
    from frappe.utils import today
    listings = frappe.get_all(
        "Featured Listing",
        filters={"status": "Active", "start_date": ("<=", today()), "end_date": (">=", today())},
        fields=["app", "placement"],
    )
    for listing in listings:
        if listing["app"] not in featured_app_names:
            app_data = frappe.db.get_value(
                "Registry App", listing["app"],
                ["app_name", "title", "description", "category", "developer", "trust_tier",
                 "rating", "install_count", "github_url", "latest_version", "icon_url",
                 "price", "pricing_type"],
                as_dict=True,
            )
            if app_data:
                app_data["placement"] = listing["placement"]
                featured.append(app_data)
                featured_app_names.add(listing["app"])

    for app in featured:
        if app.get("developer"):
            app["developer_name"] = (
                frappe.db.get_value("Registry Developer", app["developer"], "developer_name")
                or app["developer"]
            )
    return featured


# ---------------------------------------------------------------------------
# Task 0 — Security endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def get_review_nonce(app_name, instance_uuid):
    """Generate a review nonce for verified review submission."""
    from nextstar_registry.nextstar_registry.review_nonce import generate_review_nonce

    nonce = generate_review_nonce(app_name, instance_uuid)
    return {"nonce": nonce}


@frappe.whitelist()
def proxy_scan_app(github_url):
    """Proxy app scanning through the registry server."""
    from nextstar_registry.nextstar_registry.scanner_proxy import proxy_scan

    return proxy_scan(github_url)


# ---------------------------------------------------------------------------
# Phase 4 — License endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def validate_license(license_key, instance_uuid=None):
    """Validate a license key (called by customer instances)."""
    from nextstar_registry.nextstar_registry.license_manager import validate_license as _validate
    return _validate(license_key, instance_uuid)


@frappe.whitelist()
def get_license_status(license_key):
    """Get license details (authenticated)."""
    if not frappe.db.exists("App License", license_key):
        frappe.throw("License not found")
    return frappe.get_doc("App License", license_key).as_dict()


@frappe.whitelist()
def revoke_license(license_key):
    """Revoke a license (admin only)."""
    frappe.only_for("System Manager")
    from nextstar_registry.nextstar_registry.license_manager import revoke_license as _revoke
    return _revoke(license_key)


# ---------------------------------------------------------------------------
# Phase 4 — Stripe endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def create_checkout(app_name, buyer_email, success_url, cancel_url):
    """Create Stripe Checkout session for purchasing an app."""
    from nextstar_registry.nextstar_registry.stripe_integration import create_checkout_session
    return create_checkout_session(app_name, buyer_email, success_url, cancel_url)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    from nextstar_registry.nextstar_registry.stripe_integration import handle_webhook
    payload = frappe.request.get_data(as_text=True)
    sig_header = frappe.request.headers.get("Stripe-Signature", "")
    return handle_webhook(payload, sig_header)


# ---------------------------------------------------------------------------
# Phase 4 — Payout, Featured, Spotlight endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_developer_payouts(developer_email):
    """Get payout history for a developer."""
    return frappe.get_all(
        "Developer Payout",
        filters={"developer": developer_email},
        fields=["name", "period_start", "period_end", "total_sales",
                "commission_amount", "net_payout", "status"],
        order_by="period_end desc",
    )


@frappe.whitelist(allow_guest=True)
def get_featured_listings():
    """Get active featured listings."""
    from frappe.utils import today
    listings = frappe.get_all(
        "Featured Listing",
        filters={"status": "Active", "start_date": ("<=", today()), "end_date": (">=", today())},
        fields=["app", "placement"],
    )
    for l in listings:
        app_data = frappe.db.get_value(
            "Registry App", l["app"],
            ["app_name", "title", "description", "developer", "trust_tier", "rating",
             "install_count", "github_url", "latest_version", "icon_url", "price", "pricing_type"],
            as_dict=True,
        )
        if app_data:
            l.update(app_data)
            if app_data.get("developer"):
                l["developer_name"] = (
                    frappe.db.get_value("Registry Developer", app_data["developer"], "developer_name") or ""
                )
    return listings


@frappe.whitelist(allow_guest=True)
def get_developer_spotlight():
    """Get current month's developer spotlight."""
    from frappe.utils import getdate, today
    current_month = getdate(today()).replace(day=1)
    spotlight = frappe.get_all(
        "Developer Spotlight",
        filters={"month": current_month},
        fields=["developer", "title", "description", "featured_app", "photo_url"],
        limit=1,
    )
    if spotlight:
        s = spotlight[0]
        if s.get("developer"):
            s["developer_name"] = (
                frappe.db.get_value("Registry Developer", s["developer"], "developer_name") or ""
            )
        if s.get("featured_app"):
            s["app_title"] = frappe.db.get_value("Registry App", s["featured_app"], "title") or ""
        return s
    return None


@frappe.whitelist()
def purchase_featured(app_name, placement, duration_days):
    """Purchase featured placement."""
    from frappe.utils import add_days, today

    # Featured placement pricing (simple weekly pricing)
    pricing = {"Hero": 99, "Banner": 49, "Sidebar": 29}
    price_per_day = pricing.get(placement, 29)
    duration_days = int(duration_days)
    total = price_per_day * (duration_days / 7)  # Weekly pricing

    # For now, just create the featured listing directly (no payment for MVP)
    doc = frappe.get_doc({
        "doctype": "Featured Listing",
        "app": app_name,
        "start_date": today(),
        "end_date": add_days(today(), duration_days),
        "placement": placement,
        "paid_amount": total,
        "status": "Active",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "active", "end_date": str(doc.end_date)}
