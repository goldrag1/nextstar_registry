import os
import re
import shutil
import subprocess
import tempfile

import frappe


def proxy_scan(github_url):
    """Clone and scan an app on the registry server."""
    if not re.match(r'^https://github\.com/[\w.\-]+/[\w.\-]+(\.git)?$', github_url):
        frappe.throw("Invalid GitHub URL")

    tmpdir = tempfile.mkdtemp(prefix="nextstar_scan_")
    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", github_url, tmpdir],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            frappe.throw(f"Failed to clone repository: {result.stderr[:200]}")

        # Check size (max 100MB)
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, f))
            for dirpath, _, filenames in os.walk(tmpdir)
            for f in filenames
        )
        if total_size > 100 * 1024 * 1024:
            frappe.throw("Repository too large (max 100MB)")

        # Run lint (import from nextstar_cli if available, fallback to basic scan)
        try:
            from nextstar_cli.lint import run_lint_internal

            result = run_lint_internal(tmpdir)
            return {
                "scan_type": "lint",
                "findings": result["findings"],
                "safety_labels": result["safety_labels"],
                "summary": result["summary"],
                "has_critical": result["has_critical"],
                "finding_count": len(result["findings"]),
            }
        except ImportError:
            return {
                "scan_type": "unavailable",
                "findings": [],
                "summary": "Scanner not available on registry",
            }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
