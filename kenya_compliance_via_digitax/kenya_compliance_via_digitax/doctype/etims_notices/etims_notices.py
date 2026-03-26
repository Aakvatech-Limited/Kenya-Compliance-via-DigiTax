# Copyright (c) 2026, David Gitau and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class eTimsNotices(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contents: DF.TextEditor | None
		details_url: DF.Data | None
		notice_number: DF.Int
		registration_datetime: DF.Datetime | None
		title: DF.Data | None
	# end: auto-generated types

	pass
