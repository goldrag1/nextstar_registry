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
        ai_result = {}
        settings = frappe.get_single("Registry Settings")
        api_key = settings.get_password("anthropic_api_key") if settings.anthropic_api_key else None

        if api_key and (force_ai or _should_ai_scan()):
            from nextstar_registry.nextstar_registry.ai_scanner import ai_review

            max_files = int(getattr(settings, "scan_max_files", 10) or 10)
            max_size_kb = int(getattr(settings, "scan_max_size_kb", 50) or 50)
            ai_result = ai_review(tmpdir, api_key, max_files=max_files, max_size_kb=max_size_kb)
            ai_findings = ai_result.get("findings", [])
            ai_ran = ai_result.get("ai_ran", False)
            if ai_ran:
                _increment_ai_scan_count()

        # Count code lines in the cloned repo
        total_lines = 0
        total_files = 0
        for root, dirs, files in os.walk(tmpdir):
            if any(skip in root for skip in [".git", "__pycache__", "node_modules"]):
                continue
            for f in files:
                if f.endswith(".py"):
                    total_files += 1
                    try:
                        with open(os.path.join(root, f)) as fh:
                            total_lines += sum(1 for _ in fh)
                    except Exception:
                        pass

        # Merge results
        all_findings = lint_findings + ai_findings
        has_critical = any(
            f.get("severity") == "critical" for f in all_findings
        )

        # Merge metrics from AI scan if available
        metrics = ai_result.get("metrics", {}) if ai_ran else {}
        metrics["code_lines"] = metrics.get("code_lines") or total_lines
        metrics["files_count"] = metrics.get("files_count") or total_files

        return {
            "scan_type": "lint+ai" if ai_ran else lint_result.get("scan_type", "lint"),
            "findings": all_findings,
            "safety_labels": lint_result.get("safety_labels", {}),
            "summary": lint_result.get("summary", ""),
            "has_critical": has_critical or lint_result.get("has_critical", False),
            "finding_count": len(all_findings),
            "ai_ran": ai_ran,
            "model": ai_result.get("model") if ai_ran else None,
            "metrics": metrics,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def scan_submission(submission_name, github_url):
    """Background job: scan a submitted app and store results."""
    settings = frappe.get_single("Registry Settings")
    scan_mode = getattr(settings, "scan_mode", "Batch (recommended)") or "Batch (recommended)"

    submission = frappe.get_doc("App Submission", submission_name)

    # Get commit hash
    commit_hash = _get_github_head_hash(github_url)

    # Check cache
    cached = _get_cached_scan(github_url, commit_hash)
    if cached:
        _store_scan_result(submission, cached, commit_hash)
        _notify_scan_complete(submission, cached)
        return

    if scan_mode == "Disabled":
        # Just run lint, no AI
        result = proxy_scan(github_url, force_ai=False)
        _store_scan_result(submission, result, commit_hash)
        _notify_scan_complete(submission, result)
        return

    # Run lint first (always)
    try:
        lint_result = proxy_scan(github_url, force_ai=False)
    except Exception as e:
        lint_result = {
            "scan_type": "error",
            "findings": [],
            "summary": f"Lint scan failed: {str(e)[:200]}",
            "has_critical": False,
            "finding_count": 0,
            "ai_ran": False,
        }

    _store_scan_result(submission, lint_result, commit_hash)

    api_key = settings.get_password("anthropic_api_key") if settings.anthropic_api_key else None
    if not api_key:
        _notify_scan_complete(submission, lint_result)
        return

    if scan_mode == "Synchronous":
        # Sync AI scan (existing behavior)
        try:
            result = proxy_scan(github_url, force_ai=True)
        except Exception as e:
            result = {
                "scan_type": "error",
                "findings": lint_result.get("findings", []),
                "summary": f"AI scan failed: {str(e)[:200]}",
                "has_critical": lint_result.get("has_critical", False),
                "finding_count": lint_result.get("finding_count", 0),
                "ai_ran": False,
            }
        _store_scan_result(submission, result, commit_hash)
        _notify_scan_complete(submission, result)
    else:
        # Batch mode -- submit async job, results come later
        from nextstar_registry.nextstar_registry.ai_scanner import ai_review_batch

        max_files = int(getattr(settings, "scan_max_files", 10) or 10)
        max_size_kb = int(getattr(settings, "scan_max_size_kb", 50) or 50)

        tmpdir = tempfile.mkdtemp(prefix="nextstar_batch_")
        try:
            subprocess.run(
                ["git", "clone", "--depth=1", github_url, tmpdir],
                capture_output=True, timeout=120,
            )
            batch_id = ai_review_batch(
                tmpdir, api_key, submission_name,
                max_files=max_files, max_size_kb=max_size_kb,
            )
            if batch_id:
                submission.reload()
                # Store batch_id for polling
                submission.scan_result = json.dumps({
                    "batch_id": batch_id,
                    "status": "processing",
                    "lint": lint_result,
                })
                submission.save(ignore_permissions=True)
                frappe.db.commit()
            else:
                # Batch submission failed, notify with lint-only results
                _notify_scan_complete(submission, lint_result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


def _store_scan_result(submission, result, commit_hash):
    """Store scan result on the submission document."""
    submission.reload()
    submission.scan_result = json.dumps(result)
    submission.scan_commit_hash = commit_hash or ""
    submission.scan_date = frappe.utils.now_datetime()
    submission.ai_scan_ran = result.get("ai_ran", False)

    # Store model used if available
    if result.get("model"):
        submission.scan_model_used = result["model"]

    # Store metrics if available
    metrics = result.get("metrics", {})
    if metrics:
        if metrics.get("code_lines"):
            submission.scan_code_lines = metrics["code_lines"]
        if metrics.get("files_count"):
            submission.scan_files_count = metrics["files_count"]
        if metrics.get("input_tokens"):
            submission.scan_input_tokens = metrics["input_tokens"]
        if metrics.get("output_tokens"):
            submission.scan_output_tokens = metrics["output_tokens"]
        if metrics.get("cost_usd"):
            submission.scan_cost_usd = metrics["cost_usd"]
        if metrics.get("duration_seconds"):
            submission.scan_duration_seconds = metrics["duration_seconds"]

    submission.save(ignore_permissions=True)
    frappe.db.commit()


def _notify_scan_complete(submission, scan_result):
    """Notify the developer that their app scan is complete."""
    settings = frappe.get_single("Registry Settings")
    if not getattr(settings, "notify_developer_on_scan", 1):
        return

    developer_email = submission.developer
    if not developer_email:
        return

    findings = scan_result.get("findings", []) if isinstance(scan_result, dict) else []
    critical = sum(1 for f in findings if f.get("severity") == "critical")
    warnings = sum(1 for f in findings if f.get("severity") == "warning")
    info = sum(1 for f in findings if f.get("severity") == "info")
    ai_ran = scan_result.get("ai_ran", False) if isinstance(scan_result, dict) else False

    # Determine status
    if critical > 0:
        status_text = f"{critical} critical issue(s) found"
        status_color = "red"
    elif warnings > 0:
        status_text = f"{warnings} warning(s) found"
        status_color = "orange"
    else:
        status_text = "No critical issues"
        status_color = "green"

    scan_type = "AI + Static Analysis" if ai_ran else "Static Analysis Only"
    app_name = getattr(submission, "app_name", submission.name)
    version = getattr(submission, "version", "")

    subject = f"Scan Complete: {app_name} v{version} -- {status_text}"
    message = f"""<h3>App Scan Results</h3>
    <p><b>App:</b> {frappe.utils.escape_html(app_name)}</p>
    <p><b>Version:</b> {frappe.utils.escape_html(version)}</p>
    <p><b>Scan Type:</b> {scan_type}</p>
    <p><b>Status:</b> <span style="color:{status_color}; font-weight:bold;">{status_text}</span></p>
    <p><b>Results:</b> {critical} critical, {warnings} warnings, {info} info</p>
    <hr>
    <p>Your submission <b>{submission.name}</b> is now ready for review by the Nextstar team.</p>
    <p>You'll be notified when the review is complete.</p>
    <p><small>Nextstar App Store Registry</small></p>"""

    try:
        frappe.sendmail(
            recipients=[developer_email],
            subject=subject,
            message=message,
            now=True,
        )
    except Exception:
        pass  # Email may not be configured

    # Also create a notification log on the registry
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "for_user": "Administrator",
            "type": "Alert",
            "document_type": "App Submission",
            "document_name": submission.name,
            "subject": subject,
            "email_content": f"Scan for {app_name} v{version}: {status_text}",
        }).insert(ignore_permissions=True)
    except Exception:
        pass


def _notify_review_complete(submission, verdict):
    """Notify developer when their submission is reviewed."""
    developer_email = submission.developer
    if not developer_email:
        return

    app_name = getattr(submission, "app_name", submission.name)
    version = getattr(submission, "version", "")

    if verdict == "Approved":
        subject = f"Approved: {app_name} v{version}"
        message = f"""<h3>Your app has been approved!</h3>
        <p><b>{frappe.utils.escape_html(app_name)}</b> v{frappe.utils.escape_html(version)} is now live
        in the Nextstar App Store catalog.</p>
        <p>Users can now discover and install your app.</p>
        <p><small>Nextstar App Store Registry</small></p>"""
    else:
        subject = f"Rejected: {app_name} v{version}"
        message = f"""<h3>Your submission was not approved</h3>
        <p><b>{frappe.utils.escape_html(app_name)}</b> v{frappe.utils.escape_html(version)}
        did not pass review.</p>
        <p>Please address the issues and submit a new version.</p>
        <p><small>Nextstar App Store Registry</small></p>"""

    try:
        frappe.sendmail(recipients=[developer_email], subject=subject, message=message, now=True)
    except Exception:
        pass


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
            data = json.loads(cached)
            # Don't use cache if it's a pending batch scan
            if data.get("status") == "processing":
                return None
            return data
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
