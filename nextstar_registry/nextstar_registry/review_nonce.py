import frappe
import secrets


def generate_review_nonce(app_name, instance_uuid):
    """Generate a time-limited one-time-use nonce for review submission."""
    nonce = secrets.token_hex(32)
    cache_key = f"review_nonce:{nonce}"
    frappe.cache.set_value(
        cache_key,
        {"app_name": app_name, "instance_uuid": instance_uuid},
        expires_in_sec=300,
    )
    return nonce


def validate_review_nonce(nonce, app_name):
    """Validate and consume a review nonce (one-time use)."""
    cache_key = f"review_nonce:{nonce}"
    data = frappe.cache.get_value(cache_key)
    if not data:
        return False
    if data.get("app_name") != app_name:
        return False
    # Consume the nonce (one-time use)
    frappe.cache.delete_value(cache_key)
    return True
