# Nextstar Registry

Central registry API for the Nextstar App Store ecosystem. This is the server-side component that hosts the app catalog, manages developer accounts, handles app submissions with AI-powered code scanning, processes payments via Stripe, issues licenses, and aggregates health telemetry from customer instances.

Deployed on a central server (e.g. `registry.nextstar-erp.com`), it serves multiple customer sites running `nextstar_apps_store`.

## Architecture

### DocTypes

The app defines 13+ DocTypes organized around these domains:

| DocType | Purpose |
|---------|---------|
| Registry App | App catalog entries with metadata, pricing, compatibility |
| Registry Developer | Developer accounts with Stripe Connect payout info |
| App Submission | Submission workflow: draft, scanning, reviewed, approved/rejected |
| App Version | Versioned releases with changelogs and compatibility ranges |
| App Review | User reviews with star ratings and nonce-based verification |
| App Bundle | Curated app bundles with discounted pricing |
| App License | HMAC-signed license keys with instance binding and expiry |
| App Screenshot | Gallery images for app listings |
| Health Report | Telemetry reports from customer instances |
| Recommendation Rule | Rule-based engine: "if user has apps [A, B] then recommend C" |
| Featured Listing | Time-bound featured app promotions |
| Developer Payout | Monthly payout records with commission calculations |
| Registry Settings | Global configuration (signing secret, API keys, scan mode) |
| Community Reviewer | Trusted reviewers with elevated permissions |

### Developer Portal

A single-page application for developers to register, manage submissions, view analytics, and track payouts.

### API Surface

30+ whitelisted API endpoints organized by domain:

| Category | Key Endpoints |
|----------|--------------|
| Public catalog | `get_catalog`, `get_app_detail`, `search_apps`, `get_bundles` |
| Developer management | `register_developer`, `submit_app`, `submit_version` |
| Reviews | `submit_review`, `get_reviews`, `get_review_nonce` |
| Licensing | `validate_license`, `create_checkout`, `stripe_webhook` |
| Health | `report_health`, `get_health_summary` |
| Featured | `get_featured`, `get_recommendations` |

## Key Subsystems

### App Submission and AI Scanning

Developers submit apps through the portal. Each submission triggers a two-stage review: a lint scan for common issues, followed by a Claude AI code review that produces findings and safety labels. The scan can run in batch mode (recommended for large apps) or synchronous mode. Results feed into an approve/reject decision.

### License Management

Licenses are HMAC-signed keys in the format `NS-{app}-{random}-{signature}`, generated using the `license_signing_secret` from Registry Settings. Licenses bind to a specific instance on first use and support optional expiry dates.

### Archive Distribution

Private apps can upload tar.gz archives for distribution. Downloads require a valid, bound license. The registry verifies license status before serving the archive.

### Health Aggregation

Customer instances running `nextstar_apps_store` send periodic telemetry reports. The registry aggregates these into 30-day rolling averages and retains raw reports for 90 days.

### Integrity Checking

A daily scheduled task compares each approved app's `approved_commit_hash` against the current GitHub HEAD. Mismatches are flagged as potential tampering for manual review.

### Recommendations

A rule-based engine where administrators define rules like "if the user has apps [A, B], recommend C." The engine evaluates installed apps on customer instances and returns personalized suggestions.

### Developer Payouts

Monthly calculation of developer earnings with a configurable commission rate (default 15%). Generates payout records that can be processed through Stripe Connect.

## Installation

```bash
bench get-app https://github.com/goldrag1/nextstar_registry --branch develop
bench --site your-site install-app nextstar_registry
```

## Configuration

After installation, configure via **Registry Settings**:

| Setting | Required | Description |
|---------|----------|-------------|
| `license_signing_secret` | Yes | HMAC secret for license key generation |
| Stripe API keys | No | Enable payment processing and license purchases |
| Anthropic API key | No | Enable AI-powered code scanning |
| `scan_mode` | No | Batch (recommended), Synchronous, or Disabled |

## Seed Data

On install, the app creates default seed data:

- **Frappe Technologies** developer account
- 5 flagship apps: HRMS, Webshop, Helpdesk, Raven, Wiki
- 2 app bundles

## Scheduler Tasks

| Frequency | Task |
|-----------|------|
| Hourly | Poll batch scan results |
| Daily | Aggregate health reports, cleanup old reports, expire featured listings, check app integrity |
| Monthly | Calculate developer payouts |

## Dependencies

- Frappe v16+ (required)
- No additional pip dependencies beyond Frappe

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/nextstar_registry
pre-commit install
```

Tools: ruff, eslint, prettier, pyupgrade.

## CI

GitHub Actions workflows:

- **CI**: Installs the app and runs unit tests on every push to `develop`.
- **Linters**: Runs Frappe Semgrep Rules and pip-audit on every pull request.

## License

MIT
