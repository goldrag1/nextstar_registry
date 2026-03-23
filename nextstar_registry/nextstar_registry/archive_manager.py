"""Archive storage and distribution for private/paid apps."""
import hashlib

import frappe


def upload_archive(app_name, version, file_content, filename, developer_email):
    """Store an uploaded app archive on the registry.

    Args:
        app_name: The app identifier (e.g. "my_frappe_app")
        version: Semantic version string (e.g. "1.0.0")
        file_content: Raw bytes of the .tar.gz archive
        filename: Original filename (e.g. "my_frappe_app-1.0.0.tar.gz")
        developer_email: Email of the uploading developer (for audit)

    Returns:
        dict with status, file_url, hash, size
    """
    # Validate size (max 100MB)
    if len(file_content) > 100 * 1024 * 1024:
        frappe.throw("Archive too large (max 100MB)")

    # Calculate SHA256 hash
    archive_hash = hashlib.sha256(file_content).hexdigest()

    # Save as private file
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": f"{app_name}-{version}.tar.gz",
        "is_private": 1,
        "content": file_content,
        "attached_to_doctype": "Registry App",
        "attached_to_name": app_name,
    })
    file_doc.save(ignore_permissions=True)

    # Update Registry App if it exists
    if frappe.db.exists("Registry App", app_name):
        frappe.db.set_value("Registry App", app_name, {
            "distribution_type": "Archive",
            "archive_file": file_doc.file_url,
            "archive_size": len(file_content),
            "archive_hash": archive_hash,
        })

    frappe.db.commit()
    return {
        "status": "uploaded",
        "file_url": file_doc.file_url,
        "hash": archive_hash,
        "size": len(file_content),
    }


def download_archive(app_name, license_key):
    """Serve an app archive to a buyer with a valid license.

    Args:
        app_name: The app to download
        license_key: A valid App License key for this app

    Returns:
        dict with filename, content (bytes), hash

    Raises:
        frappe.AuthenticationError: If the license is invalid or mismatched
    """
    from nextstar_registry.nextstar_registry.license_manager import validate_license

    result = validate_license(license_key)
    if not result.get("valid"):
        frappe.throw(
            f"Invalid or expired license: {result.get('reason', 'unknown')}",
            frappe.AuthenticationError,
        )
    if result.get("app") != app_name:
        frappe.throw("License does not match this app", frappe.AuthenticationError)

    app = frappe.get_doc("Registry App", app_name)
    if not app.archive_file:
        frappe.throw("No archive available for this app")

    # Get file content
    file_doc = frappe.get_doc("File", {"file_url": app.archive_file})
    content = file_doc.get_content()

    return {
        "filename": f"{app_name}-{app.latest_version}.tar.gz",
        "content": content,
        "hash": app.archive_hash,
    }
