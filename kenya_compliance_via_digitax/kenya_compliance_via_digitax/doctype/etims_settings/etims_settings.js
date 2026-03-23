// Copyright (c) 2026, David Gitau and contributors
// For license information, please see license.txt

frappe.ui.form.on("eTims Settings", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.is_active) {
			frm.add_custom_button(
				__("Get Notices"),
				function () {
					frappe.call({
						method: "kenya_compliance_via_digitax.kenya_compliance_via_digitax.background_tasks.tasks.perform_notice_search",
						args: {
							settings_name: frm.doc.name,
							request_data: {
								document_name: frm.doc.name,
							},
						},
						freeze: true,
						freeze_message: __("Initiating notice search..."),
						callback: (response) => {
							frappe.msgprint({
								title: __("Success"),
								indicator: "green",
								message: __("Notice search initiated successfully."),
							});
						},
						error: (error) => {
							frappe.msgprint({
								title: __("Error"),
								indicator: "red",
								message: __("Failed to initiate notice search."),
							});
						},
					});
				},
				__("eTims Actions"),
			);
		}
	},
});
