"""AI-powered code review using Claude for Frappe app security analysis."""
import os

import frappe


def ai_review(app_path, api_key):
    """Run Claude AI security review on an app's key files.

    Returns dict with findings, summary, scan_type.
    """
    if not api_key:
        return {"findings": [], "summary": "AI review skipped — no API key", "scan_type": "ai", "ai_ran": False}

    # Collect key files
    key_files = ["hooks.py", "install.py", "api.py"]
    code_content = []

    for root, _dirs, files in os.walk(app_path):
        if any(skip in root for skip in [".git", "__pycache__", "node_modules", ".bak"]):
            continue
        for filename in files:
            if filename in key_files or (filename.endswith(".py") and "api" in filename.lower()):
                filepath = os.path.join(root, filename)
                relative_path = os.path.relpath(filepath, app_path)
                try:
                    with open(filepath) as f:
                        content = f.read()
                    if len(content) > 500:
                        code_content.append(f"=== {relative_path} ===\n{content}")
                except (OSError, UnicodeDecodeError):
                    continue

    if not code_content:
        return {"findings": [], "summary": "AI review: no key files found", "scan_type": "ai", "ai_ran": False}

    combined_code = "\n\n".join(code_content[:5])
    if len(combined_code) > 30000:
        combined_code = combined_code[:30000] + "\n... (truncated)"

    prompt = (
        "You are a security reviewer for Frappe framework apps. "
        "Review this code for security and privacy concerns. "
        "Focus on: data exfiltration, unauthorized access, command injection, "
        "SQL injection, credential exposure, and suspicious external API calls.\n\n"
        "For each finding, output exactly one line in this format:\n"
        "FINDING|severity|category|detail|file\n"
        "Where severity is critical/warning/info, category is security/privacy/quality.\n"
        "If the code is clean, output: CLEAN|No security concerns found.\n\n"
        f"Code to review:\n{combined_code}"
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response = message.content[0].text
    except Exception as e:
        frappe.logger().error(f"AI review failed: {e}")
        return {
            "findings": [],
            "summary": f"AI review failed: {str(e)[:100]}",
            "scan_type": "ai",
            "ai_ran": False,
        }

    # Parse response
    findings = []
    for line in response.strip().split("\n"):
        if line.startswith("FINDING|"):
            parts = line.split("|", 4)
            if len(parts) >= 4:
                findings.append({
                    "severity": parts[1].strip(),
                    "category": parts[2].strip(),
                    "message": parts[3].strip(),
                    "file": parts[4].strip() if len(parts) > 4 else "",
                })

    return {
        "findings": findings,
        "summary": f"AI review: {len(findings)} findings",
        "scan_type": "ai",
        "ai_ran": True,
    }
