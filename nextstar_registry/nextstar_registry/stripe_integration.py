import json

import frappe


def _get_stripe():
    """Get configured Stripe client."""
    settings = frappe.get_single("Registry Settings")
    secret_key = settings.get_password("stripe_secret_key") if settings.stripe_secret_key else None
    if not secret_key:
        frappe.throw("Stripe is not configured")
    try:
        import stripe
        stripe.api_key = secret_key
        return stripe
    except ImportError:
        frappe.throw("Stripe Python SDK not installed. Run: pip install stripe")


def create_checkout_session(app_name, buyer_email, success_url, cancel_url):
    """Create a Stripe Checkout session for purchasing an app."""
    stripe = _get_stripe()

    app = frappe.get_doc("Registry App", app_name)
    if app.pricing_type == "Free":
        frappe.throw(f"App '{app_name}' is free — no purchase needed")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": (app.currency or "usd").lower(),
                "product_data": {"name": app.title or app_name, "description": app.description or ""},
                "unit_amount": int(float(app.price or 0) * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url + "?license_key={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        customer_email=buyer_email,
        metadata={"app_name": app_name, "buyer_email": buyer_email},
    )

    return {"checkout_url": session.url, "session_id": session.id}


def handle_webhook(payload, sig_header):
    """Handle Stripe webhook event."""
    stripe = _get_stripe()
    settings = frappe.get_single("Registry Settings")
    webhook_secret = settings.get_password("stripe_webhook_secret") if settings.stripe_webhook_secret else None

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as e:
            frappe.throw(f"Webhook signature verification failed: {e}")
    else:
        event = json.loads(payload)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        app_name = metadata.get("app_name")
        buyer_email = metadata.get("buyer_email") or session.get("customer_email")
        payment_id = session.get("payment_intent") or session.get("id")

        if app_name:
            from nextstar_registry.nextstar_registry.license_manager import issue_license
            license_data = issue_license(app_name, buyer_email, stripe_payment_id=payment_id)

            # Update revenue tracking
            app = frappe.get_doc("Registry App", app_name)
            app.total_revenue = (app.total_revenue or 0) + float(session.get("amount_total", 0)) / 100
            app.save(ignore_permissions=True)
            frappe.db.commit()

            return {"status": "license_issued", "license_key": license_data["license_key"]}

    return {"status": "ignored"}
