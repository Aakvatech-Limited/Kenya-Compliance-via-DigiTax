const parentDoctype = "Sales Invoice";
const childDoctype = `${parentDoctype} Item`;
const packagingUnitDoctypeName = "eTims Packaging Unit";
const unitOfQuantityDoctypeName = "eTims Unit of Quantity";
const taxationTypeDoctypeName = "eTims Taxation Type";
const settingsDoctypeName = "eTims Settings";

frappe.realtime.on("refresh_form", function (name) {
	const currentForm = cur_frm;
	if (currentForm && currentForm.doc.name === name) {
		currentForm.reload_doc();
	}
});

frappe.ui.form.on(parentDoctype, {
	refresh: async function (frm) {
		await updateTaxAmountLabel(frm);
		if (frm.is_new()) return;
		const { message: activeSetting } = await frappe.call({
			method: "kenya_compliance_via_digitax.kenya_compliance_via_digitax.utils.get_active_settings",
			args: { doctype: settingsDoctypeName, company: frm.doc.company },
		});

		if (
			activeSetting?.length > 0 &&
			frm.doc.docstatus !== 0 &&
			!frm.doc.prevent_etims_submission
		) {
			if (!frm.doc.successfully_submitted) {
				frm.add_custom_button(
					__("Send Invoice"),
					function () {
						showSettingsModalAndExecute(
							"Send Invoice",
							activeSetting,
							(settings_name) => ({
								method: "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.sales_invoice.send_invoice_details",
								args: {
									name: frm.doc.name,
									settings_name: settings_name,
								},
								success_msg: "Invoice submission queued",
							}),
						);
					},
					__("eTims Actions"),
				);
			}

			if (frm.doc.successfully_submitted || frm.doc.digitax_id) {
				frm.add_custom_button(
					__("Sync Invoice Details"),
					function () {
						showSettingsModalAndExecute(
							"Sync Invoice",
							activeSetting,
							(settings_name) => ({
								method: "kenya_compliance_via_digitax.kenya_compliance_via_digitax.apis.apis.get_invoice_details",
								args: {
									document_name: frm.doc.name,
									invoice_type: "Sales Invoice",
									settings_name: settings_name,
									company: frm.doc.company,
									id: frm.doc.digitax_id,
								},
								success_msg: "Invoice sync queued",
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
	if (settings.length === 1) {
		const { method, args, success_msg } = getCallArgs(settings[0].name);
		frappe.call({
			method: method,
			args: args,
			freeze: true,
			freeze_message: "Processing...",
			callback: () => frappe.msgprint(__(success_msg)),
			error: (err) => {
				console.error(err);
				frappe.msgprint(__("An error occurred during the request."));
			},
		});
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __(title),
		fields: [
			{
				label: __("Select eTims Settings"),
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
		primary_action: ({ settings_name }) => {
			dialog.hide();
			const { method, args, success_msg } = getCallArgs(settings_name);
			frappe.call({
				method: method,
				args: args,
				freeze: true,
				freeze_message: "Processing...",
				callback: () => frappe.msgprint(__(success_msg)),
				error: (err) => {
					console.error(err);
					frappe.msgprint(__("An error occurred during the request."));
				},
			});
		},
	});
	dialog.show();
}

async function updateTaxAmountLabel(frm) {
	try {
		const defaultCompany = frappe.defaults.get_user_default("Company");
		if (!defaultCompany) return;

		const { message: companyDoc } = await frappe.db.get_value(
			"Company",
			defaultCompany,
			"default_currency",
		);

		if (companyDoc?.default_currency) {
			const currency = companyDoc.default_currency;

			frm.fields_dict.items.grid.update_docfield_property(
				"tax_amount",
				"label",
				`Tax Amount (${currency})`,
			);
		}
	} catch (error) {
		console.error("Error updating Tax Amount label:", error);
	}
}
