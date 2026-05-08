from typing import Any, Dict, Optional

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Sum

from ...apis.process_request import process_request
from ...utils import get_digitax_id, get_settings


def on_submit(doc: Document, method: str = None) -> None:
	settings = get_settings(company_name=doc.company)
	if doc.sent_to_etims or not settings or not settings.stock_auto_submission_enabled:
		return

	sync_stock_with_etims(doc.name)


def get_stock_movement_type(sle: Any) -> str:
	voucher_type = sle.voucher_type
	qty = float(sle.actual_qty or 0)

	if qty > 0:
		mapping = {
			"Purchase Receipt": "02",
			"Purchase Invoice": "02",
			"Stock Entry": "04",
			"Stock Reconciliation": "06",
			"Sales Invoice": "03",
			"Delivery Note": "03",
		}
		return mapping.get(voucher_type, "01")
	else:
		mapping = {
			"Sales Invoice": "11",
			"Delivery Note": "11",
			"Stock Entry": "13",
			"Stock Reconciliation": "16",
			"Purchase Receipt": "12",
			"Purchase Invoice": "12",
		}
		return mapping.get(voucher_type, "15")


def get_stock_action(qty: float) -> str:
	return "ADD" if qty > 0 else "DEDUCT"


@frappe.whitelist()
def sync_stock_with_etims(name: str) -> None:
	sle = frappe.get_doc("Stock Ledger Entry", name)

	latest_sle = frappe.db.get_value(
		"Stock Ledger Entry",
		{"item_code": sle.item_code, "company": sle.company},
		"name",
		order_by="posting_date desc, posting_time desc, creation desc",
	)

	if latest_sle != name:
		return

	fetch_etims_item_stock(sle, sle.item_code, sle.company)


def fetch_etims_item_stock(sle: Any, item_code: str, company: str) -> None:
	settings = get_settings(company_name=company)
	if not settings:
		return

	digitax_id = get_digitax_id("Item", item_code, settings.name)
	if not digitax_id:
		return

	request_data = {
		"id": digitax_id,
		"document_name": sle.name,
	}

	frappe.enqueue(
		process_request,
		request_data=request_data,
		route_key="ItemSearchReq",
		handler_function=fetch_etims_item_stock_on_success,
		doctype="Stock Ledger Entry",
		settings_name=settings.name,
		company=company,
		enqueue_after_commit=True,
	)


def fetch_etims_item_stock_on_success(
	response: dict, document_name: str, doctype: str, settings_name: str, **kwargs
) -> None:
	from ...apis.remote_response_status_handlers import get_response_data

	data = get_response_data(response)
	sle = frappe.get_doc("Stock Ledger Entry", document_name)

	etims_qty = float(data.get("stock_quantity") or 0)
	local_qty = get_total_stock(sle.company, sle.item_code)

	diff = local_qty - etims_qty
	if etims_qty != local_qty:
		submit_item_stock(
			sle=sle,
			item_code=sle.item_code,
			company=sle.company,
			settings_name=settings_name,
			item_id=data.get("id"),
			adjustment_qty=diff,
		)


def submit_item_stock(
	sle: Any,
	item_code: str,
	company: str,
	settings_name: str,
	item_id: str,
	adjustment_qty: float,
) -> None:
	request_data = {
		"action": "ADD" if adjustment_qty > 0 else "DEDUCT",
		"item_id": item_id,
		"quantity": abs(round(adjustment_qty, 4)),
		"movement_type": get_stock_movement_type(sle),
		"document_name": sle.name,
	}

	frappe.enqueue(
		process_request,
		request_data=request_data,
		route_key="StockAdjustReq",
		handler_function=submit_item_stock_on_success,
		request_method="PUT",
		doctype="Stock Ledger Entry",
		settings_name=settings_name,
		company=company,
		enqueue_after_commit=True,
	)


def submit_item_stock_on_success(
	response: dict, document_name: str, doctype: str, settings_name: str, **kwargs
) -> None:
	frappe.db.set_value("Stock Ledger Entry", document_name, "sent_to_etims", 1)


def get_total_stock(company: str, item_code: str) -> float:
	bin = frappe.qb.DocType("Bin")
	query = (
		frappe.qb.from_(bin)
		.select(Sum(bin.actual_qty))
		.where(bin.company == company)
		.where(bin.item_code == item_code)
	)
	result = query.run()
	return float(result[0][0] or 0)
