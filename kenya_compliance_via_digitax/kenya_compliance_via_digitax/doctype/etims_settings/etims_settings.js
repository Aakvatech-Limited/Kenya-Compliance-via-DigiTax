// Copyright (c) 2026, David Gitau and contributors
// For license information, please see license.txt

frappe.ui.form.on("eTims Settings", {
	refresh(frm) {
		if (!frm.is_new()) {
			override_delete(frm);
		}
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

function override_delete(frm) {
	setTimeout(() => {
		frm.page.menu.find('.dropdown-item:contains("Delete")').parent().remove();

		frm.page.add_menu_item(__("Delete"), () => {
			custom_delete_etims(frm);
		});
	}, 100);
}

function custom_delete_etims(frm) {
	frappe.confirm(
		__(
			"This will delete this setup AND all related records (mappings, logs, integration requests). Continue?",
		),
		() => {
			frm.call({
				method: "delete_mappings",
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Cleaning related records..."),
				callback: () => {
					frappe.call({
						method: "frappe.client.delete",
						args: {
							doctype: frm.doctype,
							name: frm.doc.name,
						},
						callback: () => {
							frappe.show_alert({
								message: __("Deleted successfully"),
								indicator: "green",
							});
							frappe.set_route("List", frm.doctype);
						},
					});
				},
				error: () => {
					frappe.msgprint({
						title: __("Error"),
						indicator: "red",
						message: __("Cleanup failed. Delete aborted."),
					});
				},
			});
		},
	);
}
