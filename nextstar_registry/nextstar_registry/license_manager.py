import hashlib
import hmac
import secrets

import frappe


def _get_secret():
    """Get the license signing secret from Registry Settings."""
    secret = frappe.db.get_single_value("Registry Settings", "license_signing_secret")
    if not secret:
        # Password fields need get_password()
        settings = frappe.get_single("Registry Settings")
        if settings.license_signing_secret:
            secret = settings.get_password("license_signing_secret")
    if not secret:
        frappe.throw("License signing secret not configured in Registry Settings")
    return secret


def generate_license_key(app_name):
    """Generate an HMAC-signed license key."""
    random_part = secrets.token_hex(16)
    data = f"{app_name}:{random_part}"
    sig = hmac.new(_get_secret().encode(), data.encode(), hashlib.sha256).hexdigest()[:8]
    return f"NS-{app_name}-{random_part}-{sig}"


def issue_license(app_name, buyer_email, stripe_payment_id=None):
    """Issue a new license for an app."""
    key = generate_license_key(app_name)
    doc = frappe.get_doc({
        "doctype": "App License",
        "license_key": key,
        "app": app_name,
        "buyer_email": buyer_email,
        "status": "Active",
        "issued_at": frappe.utils.now_datetime(),
        "stripe_payment_id": stripe_payment_id or "",
    })
    doc.insert(ignore_permissions=True)
    # Update license count on Registry App
    count = frappe.db.count("App License", {"app": app_name, "status": "Active"})
    frappe.db.set_value("Registry App", app_name, "license_count", count)
    frappe.db.commit()
    return {"license_key": key, "app": app_name, "status": "Active"}


def validate_license(license_key, instance_uuid=None):
    """Validate a license key. Bind to instance on first use."""
    if not frappe.db.exists("App License", license_key):
        return {"valid": False, "reason": "License key not found"}

    doc = frappe.get_doc("App License", license_key)

    if doc.status != "Active":
        return {"valid": False, "reason": f"License is {doc.status}", "app": doc.app}

    if doc.expires_at and frappe.utils.now_datetime() > frappe.utils.get_datetime(doc.expires_at):
        doc.status = "Expired"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"valid": False, "reason": "License expired", "app": doc.app}

    # Bind to instance on first use
    if instance_uuid and not doc.buyer_instance:
        doc.buyer_instance = instance_uuid
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    return {
        "valid": True,
        "app": doc.app,
        "expires_at": str(doc.expires_at) if doc.expires_at else None,
        "buyer_email": doc.buyer_email,
    }


def revoke_license(license_key):
    """Revoke a license."""
    if not frappe.db.exists("App License", license_key):
        frappe.throw("License not found")
    frappe.db.set_value("App License", license_key, "status", "Revoked")
    frappe.db.commit()
    return {"status": "Revoked"}
