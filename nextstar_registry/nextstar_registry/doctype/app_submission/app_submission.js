frappe.ui.form.on("App Submission", {
	refresh(frm) {
		if (frm.doc.status === "Pending" && !frm.doc.manual_review) {
			frm.add_custom_button(
				__("Mark as Manually Reviewed"),
				() => {
					let d = new frappe.ui.Dialog({
						title: __("Manual Review"),
						fields: [
							{
								fieldname: "notes",
								fieldtype: "Text",
								label: "Review Notes",
								description:
									"Document your findings from reviewing the code manually",
							},
						],
						primary_action_label: __("Mark Reviewed"),
						primary_action(values) {
							frappe.call({
								method: "nextstar_registry.nextstar_registry.api.mark_manually_reviewed",
								args: {
									submission_name: frm.doc.name,
									notes: values.notes || "",
								},
								callback() {
									d.hide();
									frm.reload_doc();
									frappe.show_alert({
										message: __("Marked as manually reviewed"),
										indicator: "green",
									});
								},
							});
						},
					});
					d.show();
				},
				__("Review"),
			);
		}

		// Show download link for manual review
		if (frm.doc.github_url && frm.doc.status === "Pending") {
			frm.add_custom_button(
				__("Download Code for Review"),
				() => {
					let d = new frappe.ui.Dialog({
						title: __("Download Code"),
						fields: [
							{
								fieldname: "info",
								fieldtype: "HTML",
								options: `
                                <div style="margin-bottom: 15px;">
                                    <p><b>Option 1:</b> Clone and review locally</p>
                                    <pre style="background:#1e1e1e; color:#d4d4d4; padding:12px; border-radius:8px; font-size:13px;">git clone --depth=1 ${frm.doc.github_url} /tmp/${frm.doc.app_name}\ncd /tmp/${frm.doc.app_name}\n# Review with your preferred tool</pre>
                                </div>
                                <div style="margin-bottom: 15px;">
                                    <p><b>Option 2:</b> Run nextstar lint locally</p>
                                    <pre style="background:#1e1e1e; color:#d4d4d4; padding:12px; border-radius:8px; font-size:13px;">nextstar lint /tmp/${frm.doc.app_name}</pre>
                                </div>
                                <div>
                                    <p><b>Option 3:</b> Browse on GitHub</p>
                                    <a href="${frm.doc.github_url}" target="_blank" style="color: var(--primary);">${frm.doc.github_url}</a>
                                </div>
                            `,
							},
						],
						primary_action_label: __("Close"),
						primary_action() {
							d.hide();
						},
					});
					d.show();
				},
				__("Review"),
			);
		}

		// Show scan results if available
		if (frm.doc.scan_result) {
			try {
				let result = JSON.parse(frm.doc.scan_result);
				let findings = result.findings || [];
				if (findings.length > 0) {
					let html = findings
						.map(
							(f) =>
								`<div style="padding:4px 0; border-bottom:1px solid #eee;">
                            <span style="color:${f.severity === "critical" ? "red" : f.severity === "warning" ? "orange" : "gray"}; font-weight:bold;">[${f.severity}]</span>
                            ${f.message}
                            ${f.file ? `<span style="color:gray; font-size:12px;"> — ${f.file}</span>` : ""}
                        </div>`,
						)
						.join("");
					frm.set_df_property(
						"scan_result",
						"description",
						`<details><summary><b>${findings.length} findings</b> (click to expand)</summary>${html}</details>`,
					);
				}
			} catch (e) {}
		}
	},
});
