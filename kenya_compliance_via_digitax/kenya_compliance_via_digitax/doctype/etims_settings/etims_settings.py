# Copyright (c) 2026, David Gitau and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ..doctype_names_mapping import (
    DIGITAX_ID_MAPPING_DOCTYPE_NAME,
)


class eTimsSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        api_key: DF.Password
        codes_refresh_freq_cron_format: DF.Data | None
        codes_refresh_frequency: DF.Literal["", "All", "Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Annual", "Cron"]
        company: DF.Link
        env: DF.Literal["", "Sandbox", "Production"]
        etims_country_of_origin: DF.Link | None
        etims_country_of_origin_code: DF.Data | None
        is_active: DF.Check
        item_classification: DF.Link | None
        item_classification_name: DF.SmallText | None
        item_type: DF.Link | None
        item_type_name: DF.Data | None
        max_allowed_revisions: DF.Int
        maximum_purchase_information_submission_attempts: DF.Int
        maximum_sales_information_submission_attempts: DF.Int
        maximum_stock_information_submission_attempts: DF.Int
        notices_refresh_freq_cron_format: DF.Data | None
        notices_refresh_frequency: DF.Literal["", "All", "Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Annual", "Cron"]
        packaging_unit: DF.Link | None
        packaging_unit_code: DF.Data | None
        product_type: DF.Link | None
        product_type_name: DF.Data | None
        purchase_auto_submission_enabled: DF.Check
        purchase_info_cron_format: DF.Data | None
        purchase_information_submission: DF.Literal["", "All", "Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Annual", "Cron"]
        purchase_information_submission_timeframe: DF.Duration | None
        sales_auto_submission_enabled: DF.Check
        sales_info_cron_format: DF.Data | None
        sales_information_submission: DF.Literal["", "All", "Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Annual", "Cron"]
        sales_information_submission_timeframe: DF.Duration | None
        sandbox: DF.Check
        server_url: DF.Data
        stock_auto_submission_enabled: DF.Check
        stock_info_cron_format: DF.Data | None
        stock_information_submission: DF.Literal["", "All", "Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Annual", "Cron"]
        stock_information_submission_timeframe: DF.Duration | None
        taxation_type: DF.Link | None
        taxation_type_name: DF.Data | None
        tin: DF.Data | None
        unit_of_quantity: DF.Link | None
        unit_of_quantity_code: DF.Data | None
        warehouse: DF.Link | None
    # end: auto-generated types

    def before_delete(self):
        self.delete_mappings()

    @frappe.whitelist()
    def delete_mappings(self):

        mappings = frappe.get_all(
            DIGITAX_ID_MAPPING_DOCTYPE_NAME,
            filters={"etims_setup": self.name},
            pluck="name",
        )

        for docname in mappings:
            frappe.delete_doc(
                DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                docname,
                ignore_permissions=True,
                force=True,
            )

        self.delete_logs()
        self.delete_integration_requests()

    def delete_logs(self):
        error_logs = frappe.get_all(
            "Error Log",
            filters={"reference_name": self.name},
            pluck="name",
        )

        for log in error_logs:
            frappe.delete_doc(
                "Error Log",
                log,
                ignore_permissions=True,
                force=True,
            )

    def delete_integration_requests(self):
        integration_requests = frappe.get_all(
            "Integration Request",
            filters={"reference_docname": self.name},
            pluck="name",
        )

        for req in integration_requests:
            frappe.delete_doc(
                "Integration Request",
                req,
                ignore_permissions=True,
                force=True,
            )
