frappe.pages["developer-portal"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Developer Portal",
		single_column: true,
	});
	new DeveloperPortal(page);
};

class DeveloperPortal {
	constructor(page) {
		this.page = page;
		this.$container = $(page.body);
		this.developer = null;
		this.current_tab = "dashboard";
		this.current_view = null; // for sub-views like submission detail
		this.init();
	}

	async init() {
		this.$container.html('<div class="ns-dev-portal"></div>');
		this.$root = this.$container.find(".ns-dev-portal");

		// Check for stored API key
		const key = localStorage.getItem("ns_dev_key");
		if (key) {
			try {
				this.developer = await this.dev_call("developer_login", { api_key: key });
				this.render_app();
			} catch (e) {
				localStorage.removeItem("ns_dev_key");
				this.render_login();
			}
		} else {
			this.render_login();
		}

		// Hash routing
		$(window).on("hashchange", () => this.handle_hash());
	}

	// ─── API wrapper ───────────────────────────────────────────────

	async dev_call(method, args = {}) {
		const api_key = localStorage.getItem("ns_dev_key");
		const resp = await fetch(`/api/method/nextstar_registry.nextstar_registry.api.${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Api-Key": api_key || "",
			},
			body: JSON.stringify(args),
		});
		const data = await resp.json();
		if (data.exc || !resp.ok) {
			let msg = "API error";
			if (data._server_messages) {
				try {
					const msgs = JSON.parse(data._server_messages);
					msg =
						typeof msgs[0] === "string"
							? JSON.parse(msgs[0]).message || msgs[0]
							: msgs[0];
				} catch (_) {
					msg = data._server_messages;
				}
			} else if (data.exception) {
				msg = data.exception;
			}
			throw new Error(msg);
		}
		return data.message;
	}

	// ─── Auth views ────────────────────────────────────────────────

	render_login() {
		this.page.set_title("Developer Portal");
		this.$root.html(`
            <div class="ns-auth-container">
                <div class="ns-auth-card">
                    <h2 class="ns-auth-title">Developer Portal</h2>
                    <p class="ns-auth-subtitle">Sign in with your API key to manage apps, track submissions, and view analytics.</p>
                    <div class="ns-auth-error" style="display:none"></div>
                    <div class="ns-form-group">
                        <label class="ns-label">API Key</label>
                        <div class="ns-password-wrap">
                            <input type="password" class="ns-input ns-input-key" placeholder="Enter your API key" autocomplete="off" />
                            <button type="button" class="ns-toggle-vis" aria-label="Toggle visibility">Show</button>
                        </div>
                    </div>
                    <button class="ns-btn ns-btn-primary ns-btn-full ns-btn-login">Sign In</button>
                    <div class="ns-auth-links">
                        <a href="#" class="ns-link ns-link-register">Don't have a key? Register</a>
                        <a href="#" class="ns-link ns-link-forgot">Forgot your key?</a>
                    </div>
                </div>
            </div>
        `);

		// Toggle password visibility
		this.$root.find(".ns-toggle-vis").on("click", function () {
			const $input = $(this).siblings("input");
			const is_pw = $input.attr("type") === "password";
			$input.attr("type", is_pw ? "text" : "password");
			$(this).text(is_pw ? "Hide" : "Show");
		});

		// Login
		this.$root.find(".ns-btn-login").on("click", () => this.do_login());
		this.$root.find(".ns-input-key").on("keydown", (e) => {
			if (e.key === "Enter") this.do_login();
		});

		// Links
		this.$root.find(".ns-link-register").on("click", (e) => {
			e.preventDefault();
			this.render_register();
		});
		this.$root.find(".ns-link-forgot").on("click", (e) => {
			e.preventDefault();
			this.render_forgot();
		});
	}

	async do_login() {
		const key = this.$root.find(".ns-input-key").val().trim();
		if (!key) {
			this.show_auth_error("Please enter your API key.");
			return;
		}
		const $btn = this.$root.find(".ns-btn-login");
		$btn.prop("disabled", true).text("Signing in...");
		try {
			this.developer = await this.dev_call("developer_login", { api_key: key });
			localStorage.setItem("ns_dev_key", key);
			this.render_app();
		} catch (e) {
			this.show_auth_error("Invalid API key. Please check and try again.");
			$btn.prop("disabled", false).text("Sign In");
		}
	}

	show_auth_error(msg) {
		this.$root.find(".ns-auth-error").text(msg).show();
	}

	render_register() {
		this.$root.html(`
            <div class="ns-auth-container">
                <div class="ns-auth-card">
                    <h2 class="ns-auth-title">Register as Developer</h2>
                    <p class="ns-auth-subtitle">Create your developer account to publish apps on Nextstar.</p>
                    <div class="ns-auth-error" style="display:none"></div>
                    <div class="ns-register-success" style="display:none"></div>
                    <div class="ns-register-form">
                        <div class="ns-form-group">
                            <label class="ns-label">Developer Name <span class="ns-required">*</span></label>
                            <input type="text" class="ns-input ns-input-name" placeholder="Your name or company" />
                        </div>
                        <div class="ns-form-group">
                            <label class="ns-label">Email <span class="ns-required">*</span></label>
                            <input type="email" class="ns-input ns-input-email" placeholder="you@example.com" />
                        </div>
                        <div class="ns-form-group">
                            <label class="ns-label">GitHub Username <span class="ns-optional">(optional)</span></label>
                            <input type="text" class="ns-input ns-input-github" placeholder="github-username" />
                        </div>
                        <button class="ns-btn ns-btn-primary ns-btn-full ns-btn-register">Register</button>
                    </div>
                    <div class="ns-auth-links">
                        <a href="#" class="ns-link ns-link-back-login">Already have a key? Sign in</a>
                    </div>
                </div>
            </div>
        `);

		this.$root.find(".ns-btn-register").on("click", () => this.do_register());
		this.$root.find(".ns-link-back-login").on("click", (e) => {
			e.preventDefault();
			this.render_login();
		});
	}

	async do_register() {
		const name = this.$root.find(".ns-input-name").val().trim();
		const email = this.$root.find(".ns-input-email").val().trim();
		const github = this.$root.find(".ns-input-github").val().trim();

		if (!name || !email) {
			this.show_auth_error("Developer name and email are required.");
			return;
		}

		const $btn = this.$root.find(".ns-btn-register");
		$btn.prop("disabled", true).text("Registering...");
		try {
			const result = await this.dev_call("register_developer", {
				developer_name: name,
				email: email,
				github_username: github || undefined,
			});

			// Show success with API key
			this.$root.find(".ns-register-form").hide();
			this.$root.find(".ns-auth-error").hide();
			this.$root
				.find(".ns-register-success")
				.html(
					`
                <div class="ns-success-box">
                    <h3>Registration successful</h3>
                    <p class="ns-warning-text">Save this API key securely. It will not be shown again.</p>
                    <div class="ns-code-block">
                        <code class="ns-api-key-display">${this.escape_html(result.api_key)}</code>
                        <button class="ns-btn ns-btn-small ns-btn-copy" data-copy="${this.escape_html(result.api_key)}">Copy</button>
                    </div>
                    <div class="ns-success-actions">
                        <button class="ns-btn ns-btn-primary ns-btn-go-started">Go to Getting Started</button>
                        <button class="ns-btn ns-btn-secondary ns-btn-go-login">Sign In Now</button>
                    </div>
                </div>
            `,
				)
				.show();

			this.$root.find(".ns-btn-copy").on("click", function () {
				navigator.clipboard.writeText($(this).data("copy"));
				$(this).text("Copied");
				setTimeout(() => $(this).text("Copy"), 2000);
			});

			this.$root.find(".ns-btn-go-login").on("click", () => {
				localStorage.setItem("ns_dev_key", result.api_key);
				this.developer = { developer_name: name, email: email };
				this.render_app();
			});

			this.$root.find(".ns-btn-go-started").on("click", () => {
				localStorage.setItem("ns_dev_key", result.api_key);
				this.developer = { developer_name: name, email: email };
				this.current_tab = "getting-started";
				this.render_app();
			});
		} catch (e) {
			this.show_auth_error(
				e.message || "Registration failed. The email may already be registered.",
			);
			$btn.prop("disabled", false).text("Register");
		}
	}

	render_forgot() {
		this.$root.html(`
            <div class="ns-auth-container">
                <div class="ns-auth-card">
                    <h2 class="ns-auth-title">Reset API Key</h2>
                    <p class="ns-auth-subtitle">Enter your registered email. If it exists, a new API key will be sent.</p>
                    <div class="ns-auth-error" style="display:none"></div>
                    <div class="ns-auth-success" style="display:none"></div>
                    <div class="ns-form-group">
                        <label class="ns-label">Email</label>
                        <input type="email" class="ns-input ns-input-reset-email" placeholder="you@example.com" />
                    </div>
                    <button class="ns-btn ns-btn-primary ns-btn-full ns-btn-reset">Send New Key</button>
                    <div class="ns-auth-links">
                        <a href="#" class="ns-link ns-link-back-login">Back to sign in</a>
                    </div>
                </div>
            </div>
        `);

		this.$root.find(".ns-btn-reset").on("click", async () => {
			const email = this.$root.find(".ns-input-reset-email").val().trim();
			if (!email) {
				this.show_auth_error("Please enter your email.");
				return;
			}
			const $btn = this.$root.find(".ns-btn-reset");
			$btn.prop("disabled", true).text("Sending...");
			try {
				await this.dev_call("reset_api_key", { email });
				this.$root.find(".ns-auth-error").hide();
				this.$root
					.find(".ns-auth-success")
					.text(
						"If this email is registered, a new key has been sent. Check your inbox.",
					)
					.show();
				$btn.prop("disabled", false).text("Send New Key");
			} catch (e) {
				// Still show generic message for security
				this.$root.find(".ns-auth-error").hide();
				this.$root
					.find(".ns-auth-success")
					.text(
						"If this email is registered, a new key has been sent. Check your inbox.",
					)
					.show();
				$btn.prop("disabled", false).text("Send New Key");
			}
		});

		this.$root.find(".ns-link-back-login").on("click", (e) => {
			e.preventDefault();
			this.render_login();
		});
	}

	// ─── Main app shell ────────────────────────────────────────────

	render_app() {
		this.page.set_title("Developer Portal");
		this.$root.html(`
            <div class="ns-dev-header">
                <div class="ns-dev-header-row">
                    <span class="ns-dev-welcome">Welcome, ${this.escape_html(this.developer.developer_name || "Developer")}</span>
                    <button class="ns-btn ns-btn-small ns-btn-secondary ns-btn-signout">Sign Out</button>
                </div>
                <nav class="ns-tab-nav" role="navigation" aria-label="Portal sections">
                    <button class="ns-tab" data-tab="dashboard">Dashboard</button>
                    <button class="ns-tab" data-tab="apps">My Apps</button>
                    <button class="ns-tab" data-tab="submissions">Submissions</button>
                    <button class="ns-tab" data-tab="revenue">Revenue</button>
                    <button class="ns-tab" data-tab="settings">Settings</button>
                </nav>
            </div>
            <main class="ns-tab-content" role="main"></main>
        `);

		this.$root.find(".ns-btn-signout").on("click", () => {
			localStorage.removeItem("ns_dev_key");
			this.developer = null;
			this.render_login();
		});

		this.$root.find(".ns-tab").on("click", (e) => {
			const tab = $(e.currentTarget).data("tab");
			window.location.hash = tab;
		});

		this.handle_hash();
	}

	handle_hash() {
		if (!this.developer) return;
		const hash = (window.location.hash || "#dashboard").substring(1);
		const parts = hash.split("/");
		const tab = parts[0] || "dashboard";
		const sub_id = parts[1] || null;

		this.current_tab = tab;
		this.current_view = sub_id;

		// Update active tab
		this.$root.find(".ns-tab").removeClass("active");
		this.$root.find(`.ns-tab[data-tab="${tab}"]`).addClass("active");

		const $content = this.$root.find(".ns-tab-content");
		$content.html('<div class="ns-loading">Loading...</div>');

		switch (tab) {
			case "dashboard":
				this.render_dashboard($content);
				break;
			case "apps":
				if (sub_id) this.render_app_analytics($content, sub_id);
				else this.render_my_apps($content);
				break;
			case "submissions":
				if (sub_id) this.render_submission_detail($content, sub_id);
				else this.render_submissions($content);
				break;
			case "revenue":
				this.render_revenue($content);
				break;
			case "settings":
				this.render_settings($content);
				break;
			case "getting-started":
				this.render_getting_started($content);
				break;
			default:
				this.render_dashboard($content);
		}
	}

	// ─── Dashboard ─────────────────────────────────────────────────

	async render_dashboard($el) {
		try {
			const [profile, subs_data] = await Promise.all([
				this.dev_call("get_my_profile"),
				this.dev_call("get_my_submissions", { page: 1, page_size: 5 }),
			]);

			const pending_count = subs_data.submissions.filter(
				(s) => s.status === "Pending" || s.status === "Scanning",
			).length;

			$el.html(`
                <div class="ns-stats-row">
                    ${this.stat_card(profile.total_apps || 0, "Total Apps")}
                    ${this.stat_card(profile.total_installs || 0, "Total Installs")}
                    ${this.stat_card(profile.trust_level || "---", "Trust Level")}
                    ${this.stat_card(pending_count, "Pending Reviews")}
                </div>

                <section class="ns-section">
                    <h3 class="ns-section-title">Recent Activity</h3>
                    ${
						subs_data.submissions.length === 0
							? this.empty_state(
									"No submissions yet.",
									"Publish your first app with the CLI.",
									"getting-started",
									"Getting Started Guide",
								)
							: `<div class="ns-activity-list">
                            ${subs_data.submissions
								.map(
									(s) => `
                                <a href="#submissions/${s.name}" class="ns-activity-item">
                                    <div class="ns-activity-info">
                                        <span class="ns-activity-app">${this.escape_html(s.app_name)}</span>
                                        <span class="ns-activity-version">${this.escape_html(s.version || "")}</span>
                                    </div>
                                    <div class="ns-activity-meta">
                                        ${this.status_badge(s.status)}
                                        <span class="ns-activity-date">${this.format_date(s.creation)}</span>
                                    </div>
                                </a>
                            `,
								)
								.join("")}
                        </div>`
					}
                </section>

                <section class="ns-section">
                    <h3 class="ns-section-title">Quick Actions</h3>
                    <div class="ns-quick-actions">
                        <a href="#getting-started" class="ns-btn ns-btn-secondary">Getting Started Guide</a>
                    </div>
                </section>
            `);
		} catch (e) {
			$el.html(this.error_state("Could not load dashboard.", e.message));
		}
	}

	// ─── Submissions ───────────────────────────────────────────────

	async render_submissions($el) {
		try {
			const data = await this.dev_call("get_my_submissions", { page: 1, page_size: 50 });
			const submissions = data.submissions || [];

			$el.html(`
                <div class="ns-filter-bar">
                    <button class="ns-pill active" data-filter="">All</button>
                    <button class="ns-pill" data-filter="Pending">Pending</button>
                    <button class="ns-pill" data-filter="Approved">Approved</button>
                    <button class="ns-pill" data-filter="Rejected">Rejected</button>
                </div>
                <div class="ns-submissions-list"></div>
            `);

			const render_list = (filter) => {
				const filtered = filter
					? submissions.filter((s) => s.status === filter)
					: submissions;
				const $list = $el.find(".ns-submissions-list");
				if (filtered.length === 0) {
					$list.html(
						this.empty_state(
							"No submissions yet.",
							"Publish your first app with the CLI.",
							"getting-started",
							"Getting Started Guide",
						),
					);
					return;
				}
				$list.html(
					filtered
						.map(
							(s) => `
                    <a href="#submissions/${s.name}" class="ns-submission-card">
                        <div class="ns-submission-header">
                            <span class="ns-submission-app">${this.escape_html(s.app_name)}</span>
                            <span class="ns-submission-version">${this.escape_html(s.version || "")}</span>
                        </div>
                        <div class="ns-submission-meta">
                            ${this.status_badge(s.status)}
                            <span class="ns-submission-date">${this.format_date(s.creation)}</span>
                        </div>
                    </a>
                `,
						)
						.join(""),
				);
			};

			render_list("");

			$el.find(".ns-pill").on("click", function () {
				$el.find(".ns-pill").removeClass("active");
				$(this).addClass("active");
				render_list($(this).data("filter"));
			});
		} catch (e) {
			$el.html(this.error_state("Could not load submissions.", e.message));
		}
	}

	async render_submission_detail($el, name) {
		try {
			const data = await this.dev_call("get_submission_detail", { submission_name: name });
			const sub = data;
			const scan = sub.scan_result || {};
			const timeline = sub.timeline || [];
			const findings = scan.findings || [];

			// Count findings by severity
			const counts = { critical: 0, warning: 0, info: 0 };
			findings.forEach((f) => {
				const sev = (f.severity || "info").toLowerCase();
				if (counts[sev] !== undefined) counts[sev]++;
			});

			$el.html(`
                <a href="#submissions" class="ns-back-link">&larr; Submissions</a>

                <div class="ns-detail-header">
                    <div>
                        <h2 class="ns-detail-title">${this.escape_html(sub.app_name)}</h2>
                        <span class="ns-detail-version">${this.escape_html(sub.version || "")}</span>
                        <span class="ns-detail-id">${this.escape_html(sub.name)}</span>
                    </div>
                    ${this.status_badge(sub.status)}
                </div>

                <section class="ns-section">
                    <h3 class="ns-section-title">Timeline</h3>
                    <div class="ns-timeline" role="list">
                        ${timeline
							.map(
								(step, i) => `
                            <div class="ns-timeline-step ns-timeline-${step.status}" role="listitem">
                                <div class="ns-timeline-dot${step.status === "current" ? " ns-pulse" : ""}"></div>
                                ${i < timeline.length - 1 ? '<div class="ns-timeline-line"></div>' : ""}
                                <div class="ns-timeline-label">${this.escape_html(step.step)}</div>
                                <div class="ns-timeline-date">${step.date ? this.format_date(step.date) : ""}</div>
                            </div>
                        `,
							)
							.join("")}
                    </div>
                </section>

                ${
					sub.status === "Rejected" && sub.review_notes
						? `
                    <section class="ns-section">
                        <div class="ns-rejection-box">
                            <h4>Reviewer Notes</h4>
                            <p>${this.escape_html(sub.review_notes)}</p>
                            <button class="ns-btn ns-btn-primary ns-btn-resubmit" data-sub="${this.escape_html(sub.name)}">Re-submit</button>
                        </div>
                    </section>
                `
						: ""
				}

                ${
					sub.status === "Rejected" && !sub.review_notes
						? `
                    <section class="ns-section">
                        <button class="ns-btn ns-btn-primary ns-btn-resubmit" data-sub="${this.escape_html(sub.name)}">Re-submit</button>
                    </section>
                `
						: ""
				}

                ${
					findings.length > 0 || sub.scan_date
						? `
                    <section class="ns-section">
                        <h3 class="ns-section-title">Scan Results</h3>
                        ${
							sub.scan_date
								? `
                            <div class="ns-scan-meta">
                                ${scan.model ? `<span class="ns-scan-meta-item">Model: ${this.escape_html(scan.model)}</span>` : ""}
                                ${sub.scan_cost_usd ? `<span class="ns-scan-meta-item">Cost: $${Number(sub.scan_cost_usd).toFixed(4)}</span>` : ""}
                                ${sub.scan_duration_seconds ? `<span class="ns-scan-meta-item">Duration: ${sub.scan_duration_seconds}s</span>` : ""}
                                ${sub.scan_files_count ? `<span class="ns-scan-meta-item">Files: ${sub.scan_files_count}</span>` : ""}
                            </div>
                        `
								: ""
						}

                        ${
							findings.length > 0
								? `
                            <div class="ns-finding-summary">
                                ${counts.critical ? `<span class="ns-severity-badge ns-severity-critical">${counts.critical} critical</span>` : ""}
                                ${counts.warning ? `<span class="ns-severity-badge ns-severity-warning">${counts.warning} warning</span>` : ""}
                                ${counts.info ? `<span class="ns-severity-badge ns-severity-info">${counts.info} info</span>` : ""}
                            </div>
                            <div class="ns-findings-list">
                                ${this.render_findings_grouped(findings)}
                            </div>
                        `
								: `
                            <div class="ns-clean-scan">Clean scan -- no findings.</div>
                        `
						}
                    </section>
                `
						: ""
				}
            `);

			// Resubmit handler
			$el.find(".ns-btn-resubmit").on("click", async (e) => {
				const sub_name = $(e.currentTarget).data("sub");
				$(e.currentTarget).prop("disabled", true).text("Re-submitting...");
				try {
					const result = await this.dev_call("resubmit_app", {
						submission_name: sub_name,
					});
					frappe.show_alert({
						message: `New submission created: ${result.submission}`,
						indicator: "green",
					});
					window.location.hash = `submissions/${result.submission}`;
				} catch (err) {
					frappe.show_alert({ message: err.message, indicator: "red" });
					$(e.currentTarget).prop("disabled", false).text("Re-submit");
				}
			});

			// Collapsible findings
			$el.find(".ns-finding-card").on("click", function () {
				$(this).toggleClass("ns-expanded");
			});
		} catch (e) {
			$el.html(this.error_state("Could not load submission detail.", e.message));
		}
	}

	render_findings_grouped(findings) {
		const order = ["critical", "warning", "info"];
		const grouped = {};
		findings.forEach((f) => {
			const sev = (f.severity || "info").toLowerCase();
			if (!grouped[sev]) grouped[sev] = [];
			grouped[sev].push(f);
		});

		let html = "";
		order.forEach((sev) => {
			if (!grouped[sev]) return;
			grouped[sev].forEach((f) => {
				html += `
                    <div class="ns-finding-card" tabindex="0" role="button" aria-expanded="false">
                        <div class="ns-finding-header">
                            <span class="ns-severity-badge ns-severity-${sev}">${sev.toUpperCase()}</span>
                            <span class="ns-finding-title">${this.escape_html(f.title || f.message || "Finding")}</span>
                            ${f.file ? `<span class="ns-finding-file">${this.escape_html(f.file)}${f.line ? ":" + f.line : ""}</span>` : ""}
                        </div>
                        <div class="ns-finding-body">
                            ${f.description ? `<p>${this.escape_html(f.description)}</p>` : ""}
                            ${f.suggestion ? `<div class="ns-finding-suggestion"><strong>Suggestion:</strong> ${this.escape_html(f.suggestion)}</div>` : ""}
                        </div>
                    </div>
                `;
			});
		});
		return html;
	}

	// ─── My Apps ───────────────────────────────────────────────────

	async render_my_apps($el) {
		try {
			const apps = await this.dev_call("get_my_apps");

			if (!apps || apps.length === 0) {
				$el.html(
					this.empty_state(
						"No approved apps yet.",
						"Submit your first app to get started.",
						"getting-started",
						"Getting Started Guide",
					),
				);
				return;
			}

			$el.html(`
                <div class="ns-apps-grid">
                    ${apps
						.map(
							(app) => `
                        <a href="#apps/${encodeURIComponent(app.app_name)}" class="ns-app-card">
                            <div class="ns-app-card-header">
                                ${
									app.icon_url
										? `<img src="${this.escape_html(app.icon_url)}" class="ns-app-icon" alt="" />`
										: `<div class="ns-app-icon-placeholder">${this.escape_html((app.title || app.app_name).charAt(0).toUpperCase())}</div>`
								}
                                <div>
                                    <div class="ns-app-card-title">${this.escape_html(app.title || app.app_name)}</div>
                                    <div class="ns-app-card-version">${this.escape_html(app.latest_version || "")}</div>
                                </div>
                            </div>
                            <div class="ns-app-card-stats">
                                <span>${app.install_count || 0} installs</span>
                                ${app.rating ? `<span>${this.render_stars_inline(app.rating)}</span>` : ""}
                                ${app.integrity_status ? this.integrity_badge(app.integrity_status) : ""}
                            </div>
                        </a>
                    `,
						)
						.join("")}
                </div>
            `);
		} catch (e) {
			$el.html(this.error_state("Could not load apps.", e.message));
		}
	}

	async render_app_analytics($el, app_name) {
		try {
			const data = await this.dev_call("get_app_analytics", { app_name });

			$el.html(`
                <a href="#apps" class="ns-back-link">&larr; My Apps</a>

                <div class="ns-detail-header">
                    <h2 class="ns-detail-title">${this.escape_html(app_name)}</h2>
                    ${data.integrity_status ? this.integrity_badge(data.integrity_status) : ""}
                </div>

                <div class="ns-stats-row">
                    ${this.stat_card(data.total_installs || 0, "Total Installs")}
                    ${this.stat_card(data.avg_rating ? this.render_stars_inline(data.avg_rating) + " " + data.avg_rating : "---", "Avg Rating")}
                    ${this.stat_card((data.reviews || []).length, "Reviews")}
                </div>

                <section class="ns-section">
                    <h3 class="ns-section-title">Reviews</h3>
                    ${
						!data.reviews || data.reviews.length === 0
							? '<div class="ns-empty-hint">No reviews yet. Reviews appear after users install your app.</div>'
							: `<div class="ns-reviews-list">
                            ${data.reviews.map((r) => this.render_review_card(r)).join("")}
                        </div>`
					}
                </section>

                ${
					data.health_reports && data.health_reports.length > 0
						? `
                    <section class="ns-section">
                        <h3 class="ns-section-title">Health Summary</h3>
                        <div class="ns-health-summary">
                            ${data.health_reports
								.slice(0, 5)
								.map(
									(h) => `
                                <div class="ns-health-row">
                                    <span class="ns-health-date">${this.format_date(h.report_date)}</span>
                                    <span>Errors: ${h.error_count || 0}</span>
                                    <span>Scheduler: ${h.scheduler_success_rate != null ? h.scheduler_success_rate + "%" : "---"}</span>
                                    <span>Frappe ${this.escape_html(h.frappe_version || "")}</span>
                                </div>
                            `,
								)
								.join("")}
                        </div>
                    </section>
                `
						: ""
				}

                ${
					data.submission_history && data.submission_history.length > 0
						? `
                    <section class="ns-section">
                        <h3 class="ns-section-title">Submission History</h3>
                        <div class="ns-activity-list">
                            ${data.submission_history
								.map(
									(s) => `
                                <a href="#submissions/${s.name}" class="ns-activity-item">
                                    <div class="ns-activity-info">
                                        <span class="ns-activity-version">${this.escape_html(s.version || "")}</span>
                                    </div>
                                    <div class="ns-activity-meta">
                                        ${this.status_badge(s.status)}
                                        <span class="ns-activity-date">${this.format_date(s.creation)}</span>
                                    </div>
                                </a>
                            `,
								)
								.join("")}
                        </div>
                    </section>
                `
						: ""
				}
            `);

			// Respond to review handlers
			$el.find(".ns-btn-respond").on("click", function () {
				const $card = $(this).closest(".ns-review-card");
				$card.find(".ns-review-respond-form").toggle();
				$(this).text(
					$card.find(".ns-review-respond-form").is(":visible") ? "Cancel" : "Respond",
				);
			});

			$el.find(".ns-btn-submit-response").on("click", async (e) => {
				const $btn = $(e.currentTarget);
				const review_name = $btn.data("review");
				const $form = $btn.closest(".ns-review-respond-form");
				const text = $form.find("textarea").val().trim();
				if (!text) return;

				$btn.prop("disabled", true).text("Sending...");
				try {
					await this.dev_call("respond_to_review", {
						review_name: review_name,
						response_text: text,
					});
					frappe.show_alert({ message: "Response posted.", indicator: "green" });
					this.render_app_analytics($el, app_name);
				} catch (err) {
					frappe.show_alert({ message: err.message, indicator: "red" });
					$btn.prop("disabled", false).text("Submit Response");
				}
			});
		} catch (e) {
			$el.html(this.error_state("Could not load app analytics.", e.message));
		}
	}

	render_review_card(r) {
		return `
            <div class="ns-review-card">
                <div class="ns-review-header">
                    <span class="ns-review-stars">${this.render_stars_inline(r.rating)}</span>
                    <span class="ns-review-author">${this.escape_html(r.reviewer_email || "Anonymous")}</span>
                    <span class="ns-review-date">${this.format_date(r.creation)}</span>
                </div>
                ${r.title ? `<div class="ns-review-title">${this.escape_html(r.title)}</div>` : ""}
                ${r.body ? `<div class="ns-review-body">${this.escape_html(r.body)}</div>` : ""}
                ${
					r.developer_response
						? `
                    <div class="ns-developer-response">
                        <strong>Developer Response</strong>
                        <p>${this.escape_html(r.developer_response)}</p>
                        ${r.developer_response_date ? `<span class="ns-review-date">${this.format_date(r.developer_response_date)}</span>` : ""}
                    </div>
                `
						: `
                    <button class="ns-btn ns-btn-small ns-btn-secondary ns-btn-respond">Respond</button>
                    <div class="ns-review-respond-form" style="display:none">
                        <textarea class="ns-input ns-textarea" rows="3" placeholder="Write your response..."></textarea>
                        <button class="ns-btn ns-btn-small ns-btn-primary ns-btn-submit-response" data-review="${this.escape_html(r.name)}">Submit Response</button>
                    </div>
                `
				}
            </div>
        `;
	}

	// ─── Revenue ───────────────────────────────────────────────────

	async render_revenue($el) {
		try {
			const data = await this.dev_call("get_my_revenue");

			const has_data =
				data.total_revenue > 0 ||
				(data.payouts && data.payouts.length > 0) ||
				(data.recent_sales && data.recent_sales.length > 0);

			if (!has_data) {
				$el.html(
					this.empty_state(
						"No paid apps yet.",
						"Add pricing when you publish your app to start earning revenue.",
						"getting-started",
						"Publishing Guide",
					),
				);
				return;
			}

			$el.html(`
                <div class="ns-stats-row">
                    ${this.stat_card(this.format_currency(data.total_revenue), "Total Revenue")}
                    ${this.stat_card(this.format_currency(data.total_paid), "Paid Out")}
                    ${this.stat_card(this.format_currency(data.pending), "Pending")}
                </div>

                ${
					data.payouts && data.payouts.length > 0
						? `
                    <section class="ns-section">
                        <h3 class="ns-section-title">Payout History</h3>
                        <div class="ns-table-wrap">
                            <table class="ns-table">
                                <thead>
                                    <tr>
                                        <th>Period</th>
                                        <th>Sales</th>
                                        <th>Net Payout</th>
                                        <th>Status</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.payouts
										.map(
											(p) => `
                                        <tr>
                                            <td>${this.format_date(p.period_start)} - ${this.format_date(p.period_end)}</td>
                                            <td>${this.format_currency(p.total_sales)}</td>
                                            <td>${this.format_currency(p.net_payout)}</td>
                                            <td>${this.status_badge(p.status)}</td>
                                            <td>${p.payout_date ? this.format_date(p.payout_date) : "---"}</td>
                                        </tr>
                                    `,
										)
										.join("")}
                                </tbody>
                            </table>
                        </div>
                    </section>
                `
						: ""
				}

                ${
					data.recent_sales && data.recent_sales.length > 0
						? `
                    <section class="ns-section">
                        <h3 class="ns-section-title">Recent Sales</h3>
                        <div class="ns-table-wrap">
                            <table class="ns-table">
                                <thead>
                                    <tr><th>App</th><th>Buyer</th><th>Status</th><th>Date</th></tr>
                                </thead>
                                <tbody>
                                    ${data.recent_sales
										.map(
											(s) => `
                                        <tr>
                                            <td>${this.escape_html(s.app || "")}</td>
                                            <td>${this.mask_email(s.buyer_email || "")}</td>
                                            <td>${this.status_badge(s.status)}</td>
                                            <td>${this.format_date(s.issued_at)}</td>
                                        </tr>
                                    `,
										)
										.join("")}
                                </tbody>
                            </table>
                        </div>
                    </section>
                `
						: ""
				}
            `);
		} catch (e) {
			$el.html(this.error_state("Could not load revenue data.", e.message));
		}
	}

	// ─── Settings ──────────────────────────────────────────────────

	async render_settings($el) {
		try {
			const profile = await this.dev_call("get_my_profile");
			const stored_key = localStorage.getItem("ns_dev_key") || "";
			const masked_key =
				stored_key.length > 12
					? stored_key.substring(0, 8) +
						"****" +
						stored_key.substring(stored_key.length - 4)
					: "****";

			$el.html(`
                <section class="ns-section">
                    <h3 class="ns-section-title">Profile</h3>
                    <div class="ns-settings-form">
                        <div class="ns-form-group">
                            <label class="ns-label">Developer Name</label>
                            <input type="text" class="ns-input ns-settings-name" value="${this.escape_html(profile.developer_name || "")}" />
                        </div>
                        <div class="ns-form-group">
                            <label class="ns-label">Bio</label>
                            <textarea class="ns-input ns-textarea ns-settings-bio" rows="3">${this.escape_html(profile.bio || "")}</textarea>
                        </div>
                        <div class="ns-form-group">
                            <label class="ns-label">Website</label>
                            <input type="text" class="ns-input ns-settings-website" value="${this.escape_html(profile.website || "")}" />
                        </div>
                        <div class="ns-form-group">
                            <label class="ns-label">GitHub Username</label>
                            <input type="text" class="ns-input ns-settings-github" value="${this.escape_html(profile.github_username || "")}" />
                        </div>
                        <button class="ns-btn ns-btn-primary ns-btn-save-profile">Save Profile</button>
                    </div>
                </section>

                <section class="ns-section">
                    <h3 class="ns-section-title">API Key</h3>
                    <div class="ns-key-info">
                        <div class="ns-code-block">
                            <code>${masked_key}</code>
                        </div>
                        <button class="ns-btn ns-btn-secondary ns-btn-regen-key">Regenerate Key</button>
                    </div>
                    <div class="ns-new-key-display" style="display:none"></div>
                </section>
            `);

			// Save profile
			$el.find(".ns-btn-save-profile").on("click", async (e) => {
				const $btn = $(e.currentTarget);
				$btn.prop("disabled", true).text("Saving...");
				try {
					await this.dev_call("update_my_profile", {
						developer_name: $el.find(".ns-settings-name").val().trim(),
						bio: $el.find(".ns-settings-bio").val(),
						website: $el.find(".ns-settings-website").val().trim(),
						github_username: $el.find(".ns-settings-github").val().trim(),
					});
					frappe.show_alert({ message: "Profile updated.", indicator: "green" });
					$btn.prop("disabled", false).text("Save Profile");
				} catch (err) {
					frappe.show_alert({ message: err.message, indicator: "red" });
					$btn.prop("disabled", false).text("Save Profile");
				}
			});

			// Regenerate key
			$el.find(".ns-btn-regen-key").on("click", () => {
				frappe.confirm(
					"This will invalidate your current key. CLI and CI pipelines will stop working until you update the key. Continue?",
					async () => {
						try {
							const result = await this.dev_call("regenerate_api_key");
							localStorage.setItem("ns_dev_key", result.api_key);
							$el.find(".ns-new-key-display")
								.html(
									`
                                <div class="ns-success-box">
                                    <p class="ns-warning-text">Save this key securely. Update your CLI and CI.</p>
                                    <div class="ns-code-block">
                                        <code>${this.escape_html(result.api_key)}</code>
                                        <button class="ns-btn ns-btn-small ns-btn-copy" data-copy="${this.escape_html(result.api_key)}">Copy</button>
                                    </div>
                                </div>
                            `,
								)
								.show();
							$el.find(".ns-new-key-display .ns-btn-copy").on("click", function () {
								navigator.clipboard.writeText($(this).data("copy"));
								$(this).text("Copied");
								setTimeout(() => $(this).text("Copy"), 2000);
							});
						} catch (err) {
							frappe.show_alert({ message: err.message, indicator: "red" });
						}
					},
				);
			});
		} catch (e) {
			$el.html(this.error_state("Could not load settings.", e.message));
		}
	}

	// ─── Getting Started Guide ─────────────────────────────────────

	render_getting_started($el) {
		const api_key = localStorage.getItem("ns_dev_key") || "YOUR_API_KEY";

		$el.html(`
            <a href="#dashboard" class="ns-back-link">&larr; Dashboard</a>
            <div class="ns-guide">
                <h2 class="ns-guide-title">Getting Started with Nextstar</h2>

                <div class="ns-guide-step">
                    <div class="ns-guide-step-num">1</div>
                    <div class="ns-guide-step-content">
                        <h4>Install the CLI</h4>
                        <div class="ns-code-block">
                            <code>pip install nextstar-cli</code>
                            <button class="ns-btn ns-btn-small ns-btn-copy" data-copy="pip install nextstar-cli">Copy</button>
                        </div>
                    </div>
                </div>

                <div class="ns-guide-step">
                    <div class="ns-guide-step-num">2</div>
                    <div class="ns-guide-step-content">
                        <h4>Navigate to your app</h4>
                        <div class="ns-code-block">
                            <code>cd ~/frappe-bench/apps/your_app</code>
                            <button class="ns-btn ns-btn-small ns-btn-copy" data-copy="cd ~/frappe-bench/apps/your_app">Copy</button>
                        </div>
                    </div>
                </div>

                <div class="ns-guide-step">
                    <div class="ns-guide-step-num">3</div>
                    <div class="ns-guide-step-content">
                        <h4>Lint your app (free, instant)</h4>
                        <div class="ns-code-block">
                            <code>nextstar lint .</code>
                            <button class="ns-btn ns-btn-small ns-btn-copy" data-copy="nextstar lint .">Copy</button>
                        </div>
                    </div>
                </div>

                <div class="ns-guide-step">
                    <div class="ns-guide-step-num">4</div>
                    <div class="ns-guide-step-content">
                        <h4>Publish to Nextstar</h4>
                        <div class="ns-code-block">
                            <code>nextstar publish . \\
  --registry https://registry.nextstar-erp.com \\
  --api-key ${this.escape_html(api_key)} \\
  --version 1.0.0</code>
                            <button class="ns-btn ns-btn-small ns-btn-copy" data-copy="nextstar publish . --registry https://registry.nextstar-erp.com --api-key ${api_key} --version 1.0.0">Copy</button>
                        </div>
                    </div>
                </div>

                <div class="ns-guide-step">
                    <div class="ns-guide-step-num">5</div>
                    <div class="ns-guide-step-content">
                        <h4>Track your submission</h4>
                        <p>Come back to this portal to see scan results and track your app's journey through review.</p>
                        <a href="#submissions" class="ns-btn ns-btn-secondary">View Submissions</a>
                    </div>
                </div>
            </div>
        `);

		$el.find(".ns-btn-copy").on("click", function () {
			navigator.clipboard.writeText($(this).data("copy"));
			$(this).text("Copied");
			setTimeout(() => $(this).text("Copy"), 2000);
		});
	}

	// ─── Helpers ───────────────────────────────────────────────────

	stat_card(value, label) {
		return `
            <div class="ns-stat-card">
                <div class="ns-stat-number">${value}</div>
                <div class="ns-stat-label">${label}</div>
            </div>
        `;
	}

	status_badge(status) {
		const cls =
			{
				Approved: "ns-badge-approved",
				Active: "ns-badge-approved",
				Paid: "ns-badge-approved",
				Pending: "ns-badge-pending",
				Scanning: "ns-badge-pending",
				"Under Review": "ns-badge-pending",
				Rejected: "ns-badge-rejected",
				Revoked: "ns-badge-rejected",
			}[status] || "ns-badge-pending";
		return `<span class="ns-status-badge ${cls}">${this.escape_html(status || "")}</span>`;
	}

	integrity_badge(status) {
		if (!status) return "";
		const cls = status === "Verified" ? "ns-badge-approved" : "ns-badge-pending";
		return `<span class="ns-status-badge ${cls}">${this.escape_html(status)}</span>`;
	}

	render_stars_inline(rating) {
		const r = Math.round(Number(rating) || 0);
		let stars = "";
		for (let i = 1; i <= 5; i++) {
			stars +=
				i <= r
					? '<span class="ns-star ns-star-filled">&#9733;</span>'
					: '<span class="ns-star ns-star-empty">&#9733;</span>';
		}
		return stars;
	}

	empty_state(title, description, link_hash, link_text) {
		return `
            <div class="ns-empty-state">
                <p class="ns-empty-title">${title}</p>
                <p class="ns-empty-desc">${description}</p>
                ${link_hash ? `<a href="#${link_hash}" class="ns-btn ns-btn-primary">${link_text}</a>` : ""}
            </div>
        `;
	}

	error_state(title, detail) {
		return `
            <div class="ns-error-state">
                <p class="ns-error-title">${title}</p>
                <p class="ns-error-detail">${this.escape_html(detail || "")}</p>
                <button class="ns-btn ns-btn-secondary" onclick="location.reload()">Retry</button>
            </div>
        `;
	}

	format_date(dt) {
		if (!dt) return "";
		try {
			const d = new Date(dt);
			if (isNaN(d.getTime())) return "";
			return d.toLocaleDateString("en-US", {
				month: "short",
				day: "numeric",
				year: "numeric",
			});
		} catch (_) {
			return "";
		}
	}

	format_currency(val) {
		const n = Number(val) || 0;
		return (
			"$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
		);
	}

	mask_email(email) {
		if (!email) return "";
		const parts = email.split("@");
		if (parts.length !== 2) return email;
		const local = parts[0];
		return local.substring(0, 2) + "***@" + parts[1];
	}

	escape_html(str) {
		if (str == null) return "";
		return String(str)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#039;");
	}
}
