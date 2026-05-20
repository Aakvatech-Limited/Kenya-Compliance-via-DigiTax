frappe.ui.form.on("Stock Ledger Entry", {
	refresh: async function (frm) {
		if (frm.is_new()) return;

		const { message: activeSetting } = await frappe.call({
			method: "kenya_compliance_via_digitax.kenya_compliance_via_digitax.utils.get_active_settings",
			args: { company: frm.doc.company },
		});

		if (
			activeSetting?.length > 0 &&
			frm.doc.docstatus !== 0 &&
			!frm.doc.prevent_etims_submission
		) {
			if (!frm.doc.sent_to_etims) {
				frm.add_custom_button(
					__("Sync Stock to eTims"),
					function () {
						showSettingsModalAndExecute(
							"Sync Stock",
							activeSetting,
							(settings_name) => ({
								method: "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.stock_ledger_entry.sync_stock_with_etims",
								args: {
									name: frm.doc.name,
								},
								success_msg: "Stock synchronization queued",
							}),
						);
					},
					__("eTims Actions"),
				);
			}
		}
	},
});

function showSettingsModalAndExecute(title, settings, getCallArgs) {
	const executeCall = (settings_name) => {
		const { method, args, success_msg } = getCallArgs(settings_name);
		frappe.call({
			method: method,
			args: args,
			freeze: true,
			freeze_message: __("Processing..."),
			callback: (r) => {
				if (!r.exc) frappe.msgprint(__(success_msg));
			},
		});
	};

	if (settings.length === 1) {
		executeCall(settings[0].name);
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __(title),
		fields: [
			{
				label: __("Select DigiTax eTims Settings"),
				fieldname: "settings_name",
				fieldtype: "Select",
				options: settings.map((s) => ({
					label: `${s.company} (${s.name})`,
					value: s.name,
				})),
				reqd: 1,
				default: settings[0]?.name,
			},
		],
		primary_action_label: __("Proceed"),
		primary_action: (values) => {
			dialog.hide();
			executeCall(values.settings_name);
		},
	});
	dialog.show();
}
