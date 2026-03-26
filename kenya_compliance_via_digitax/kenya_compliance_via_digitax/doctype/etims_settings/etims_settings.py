# Copyright (c) 2026, David Gitau and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ..doctype_names_mapping import (
    DIGITAX_ID_MAPPING_DOCTYPE_NAME,
)


class eTimsSettings(Document):
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
