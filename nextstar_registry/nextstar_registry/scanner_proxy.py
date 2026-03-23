import json
import os
import re
import shutil
import subprocess
import tempfile

import frappe


def proxy_scan(github_url, force_ai=False):
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
        lint_findings = []
        lint_result = {}
        try:
            from nextstar_cli.lint import run_lint_internal

            lint_result = run_lint_internal(tmpdir)
            lint_findings = lint_result.get("findings", [])
        except ImportError:
            lint_result = {
                "scan_type": "unavailable",
                "findings": [],
                "summary": "Scanner not available on registry",
            }

        # AI scan
        ai_findings = []
        ai_ran = False
        settings = frappe.get_single("Registry Settings")
        api_key = settings.get_password("anthropic_api_key") if settings.anthropic_api_key else None

        if api_key and (force_ai or _should_ai_scan()):
            from nextstar_registry.nextstar_registry.ai_scanner import ai_review

            ai_result = ai_review(tmpdir, api_key)
            ai_findings = ai_result.get("findings", [])
            ai_ran = ai_result.get("ai_ran", False)
            if ai_ran:
                _increment_ai_scan_count()

        # Merge results
        all_findings = lint_findings + ai_findings
        has_critical = any(
            f.get("severity") == "critical" for f in all_findings
        )

        return {
            "scan_type": "lint+ai" if ai_ran else lint_result.get("scan_type", "lint"),
            "findings": all_findings,
            "safety_labels": lint_result.get("safety_labels", {}),
            "summary": lint_result.get("summary", ""),
            "has_critical": has_critical or lint_result.get("has_critical", False),
            "finding_count": len(all_findings),
            "ai_ran": ai_ran,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def scan_submission(submission_name, github_url):
    """Background job: scan a submitted app and store results."""
    submission = frappe.get_doc("App Submission", submission_name)

    # Get commit hash
    commit_hash = _get_github_head_hash(github_url)

    # Check cache
    cached = _get_cached_scan(github_url, commit_hash)
    if cached:
        submission.scan_result = json.dumps(cached)
        submission.scan_commit_hash = commit_hash
        submission.scan_date = frappe.utils.now_datetime()
        submission.ai_scan_ran = cached.get("ai_ran", False)
        submission.save(ignore_permissions=True)
        frappe.db.commit()
        return

    # Run fresh scan
    try:
        result = proxy_scan(github_url, force_ai=True)
    except Exception as e:
        result = {
            "scan_type": "error",
            "findings": [],
            "summary": f"Scan failed: {str(e)[:200]}",
            "has_critical": False,
            "finding_count": 0,
            "ai_ran": False,
        }

    submission.reload()
    submission.scan_result = json.dumps(result)
    submission.scan_commit_hash = commit_hash or ""
    submission.scan_date = frappe.utils.now_datetime()
    submission.ai_scan_ran = result.get("ai_ran", False)
    submission.save(ignore_permissions=True)
    frappe.db.commit()


def _get_github_head_hash(github_url):
    """Get HEAD commit hash without cloning."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", github_url, "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.split()[0]
    except Exception:
        pass
    return None


def _get_cached_scan(github_url, commit_hash):
    """Return cached scan if same repo+commit already scanned."""
    if not commit_hash:
        return None
    cached = frappe.db.get_value(
        "App Submission",
        {"github_url": github_url, "scan_commit_hash": commit_hash, "scan_result": ("!=", "")},
        "scan_result",
    )
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    return None


def _should_ai_scan():
    """Check if AI scan budget allows another scan."""
    settings = frappe.get_single("Registry Settings")
    today = frappe.utils.today()
    if str(getattr(settings, "ai_scan_daily_reset", "") or "") != today:
        frappe.db.set_single_value("Registry Settings", "ai_scan_daily_count", 0)
        frappe.db.set_single_value("Registry Settings", "ai_scan_daily_reset", today)
        frappe.db.commit()
        return True
    daily_limit = int(getattr(settings, "ai_scan_daily_budget", 5) or 5) * 20
    current = int(getattr(settings, "ai_scan_daily_count", 0) or 0)
    return current < daily_limit


def _increment_ai_scan_count():
    """Increment daily AI scan counter."""
    settings = frappe.get_single("Registry Settings")
    count = int(getattr(settings, "ai_scan_daily_count", 0) or 0) + 1
    frappe.db.set_single_value("Registry Settings", "ai_scan_daily_count", count)
    frappe.db.commit()
