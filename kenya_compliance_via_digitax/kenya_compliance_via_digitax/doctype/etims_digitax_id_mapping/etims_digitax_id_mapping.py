# Copyright (c) 2026, David Gitau and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class eTimsDigitaxIDMapping(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link
		digitax_id: DF.Data
		disabled: DF.Check
		etims_code: DF.Data | None
		etims_setup: DF.Link
		imported_item_submitted: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sent_to_etims: DF.Check
		submission_tries: DF.Int
	# end: auto-generated types

	pass
