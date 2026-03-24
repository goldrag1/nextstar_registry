"""AI-powered code review using Claude for Frappe app security analysis."""
import os
import time

import frappe

# Pricing per model (per million tokens)
MODEL_PRICING = {
    "claude-opus-4-0": {"input": 15, "output": 75},      # $15/MTok in, $75/MTok out
    "claude-sonnet-4-5": {"input": 3, "output": 15},      # $3/MTok in, $15/MTok out
}
BATCH_DISCOUNT = 0.5  # 50% off for batch


def _calculate_cost(model, input_tokens, output_tokens, is_batch=False):
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-opus-4-0"])
    discount = BATCH_DISCOUNT if is_batch else 1.0
    cost = (input_tokens * pricing["input"] * discount / 1_000_000) + \
           (output_tokens * pricing["output"] * discount / 1_000_000)
    return round(cost, 4)


def ai_review(app_path, api_key, max_files=10, max_size_kb=50):
    """Run Claude AI security review on an app's key files (synchronous).

    Returns dict with findings, summary, scan_type.
    """
    if not api_key:
        return {"findings": [], "summary": "AI review skipped — no API key", "scan_type": "ai", "ai_ran": False}

    code_content = _collect_key_files(app_path, max_files=max_files, max_size_kb=max_size_kb)
    if not code_content:
        return {"findings": [], "summary": "AI review: no key files found", "scan_type": "ai", "ai_ran": False}

    code_lines = code_content.count('\n') if code_content else 0
    files_count = code_content.count('=== ') if code_content else 0

    prompt = _build_review_prompt(code_content)

    # Get model from settings
    settings = frappe.get_single("Registry Settings")
    model = getattr(settings, "scan_model", "claude-opus-4-0") or "claude-opus-4-0"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        start = time.time()
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        duration = time.time() - start
        response = message.content[0].text
    except Exception as e:
        frappe.logger().error(f"AI review failed: {e}")
        return {
            "findings": [],
            "summary": f"AI review failed: {str(e)[:100]}",
            "scan_type": "ai",
            "ai_ran": False,
        }

    findings = _parse_review_response(response)

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    cost = _calculate_cost(model, input_tokens, output_tokens, is_batch=False)

    return {
        "findings": findings,
        "summary": f"AI review: {len(findings)} findings",
        "scan_type": "ai",
        "ai_ran": True,
        "model": model,
        "metrics": {
            "code_lines": code_lines,
            "files_count": files_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "duration_seconds": round(duration, 2),
        },
    }


def ai_review_batch(app_path, api_key, submission_name, max_files=10, max_size_kb=50):
    """Submit an AI review as a batch job (50% cheaper, async).

    Returns batch_id. Results are polled by a scheduler job.
    """
    code_content = _collect_key_files(app_path, max_files=max_files, max_size_kb=max_size_kb)
    if not code_content:
        return None

    code_lines = code_content.count('\n') if code_content else 0
    files_count = code_content.count('=== ') if code_content else 0

    # Store pre-scan metrics on submission
    if frappe.db.exists("App Submission", submission_name):
        frappe.db.set_value("App Submission", submission_name, {
            "scan_code_lines": code_lines,
            "scan_files_count": files_count,
        })
        frappe.db.commit()

    # Get model from settings
    settings = frappe.get_single("Registry Settings")
    model = getattr(settings, "scan_model", "claude-opus-4-0") or "claude-opus-4-0"

    # Store model used on submission
    if frappe.db.exists("App Submission", submission_name):
        frappe.db.set_value("App Submission", submission_name, "scan_model_used", model)
        frappe.db.commit()

    prompt = _build_review_prompt(code_content)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        batch = client.messages.batches.create(
            requests=[
                {
                    "custom_id": submission_name,
                    "params": {
                        "model": model,
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                }
            ]
        )

        return batch.id
    except Exception as e:
        frappe.logger().error(f"AI batch submission failed: {e}")
        return None


def check_batch_result(batch_id, api_key):
    """Check if a batch job has completed. Returns results or None if still processing."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != "ended":
        return None  # Still processing

    # Get results
    results = []
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            msg = result.result.message
            response_text = msg.content[0].text
            findings = _parse_review_response(response_text)
            input_tokens = msg.usage.input_tokens
            output_tokens = msg.usage.output_tokens

            # Look up the model used from the submission
            model = "claude-opus-4-0"  # default
            if result.custom_id and frappe.db.exists("App Submission", result.custom_id):
                stored_model = frappe.db.get_value(
                    "App Submission", result.custom_id, "scan_model_used"
                )
                if stored_model:
                    model = stored_model

            cost = _calculate_cost(model, input_tokens, output_tokens, is_batch=True)

            results.append({
                "custom_id": result.custom_id,
                "findings": findings,
                "summary": f"AI review: {len(findings)} findings",
                "ai_ran": True,
                "model": model,
                "metrics": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost,
                },
            })
        else:
            results.append({
                "custom_id": result.custom_id,
                "findings": [],
                "summary": f"AI review failed: {result.result.type}",
                "ai_ran": False,
            })

    return results


def _collect_key_files(app_path, max_files=10, max_size_kb=50):
    """Collect key files for review."""
    key_files = ["hooks.py", "install.py", "api.py"]
    code_content = []
    total_size = 0
    max_size = max_size_kb * 1024

    for root, _dirs, files in os.walk(app_path):
        if any(skip in root for skip in [".git", "__pycache__", "node_modules", ".bak"]):
            continue
        for filename in files:
            if len(code_content) >= max_files:
                break
            if filename in key_files or (filename.endswith(".py") and "api" in filename.lower()):
                filepath = os.path.join(root, filename)
                relative_path = os.path.relpath(filepath, app_path)
                try:
                    with open(filepath) as f:
                        content = f.read()
                    if len(content) > 500 and total_size + len(content) < max_size:
                        code_content.append(f"=== {relative_path} ===\n{content}")
                        total_size += len(content)
                except (OSError, UnicodeDecodeError):
                    continue

    return "\n\n".join(code_content) if code_content else ""


def _build_review_prompt(code_content):
    """Build the review prompt."""
    return (
        "You are a security reviewer for Frappe framework apps. "
        "Review this code for security and privacy concerns. "
        "Focus on: data exfiltration, unauthorized access, command injection, "
        "SQL injection, credential exposure, and suspicious external API calls.\n\n"
        "For each finding, output exactly one line in this format:\n"
        "FINDING|severity|category|detail|file\n"
        "Where severity is critical/warning/info, category is security/privacy/quality.\n"
        "If the code is clean, output: CLEAN|No security concerns found.\n\n"
        f"Code to review:\n{code_content}"
    )


def _parse_review_response(response_text):
    """Parse Claude's review response into findings."""
    findings = []
    for line in response_text.strip().split("\n"):
        if line.startswith("FINDING|"):
            parts = line.split("|", 4)
            if len(parts) >= 4:
                findings.append({
                    "severity": parts[1].strip(),
                    "category": parts[2].strip(),
                    "message": parts[3].strip(),
                    "file": parts[4].strip() if len(parts) > 4 else "",
                })
    return findings
