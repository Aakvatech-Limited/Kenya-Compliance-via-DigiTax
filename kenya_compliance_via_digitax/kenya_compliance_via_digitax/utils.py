"""Utility functions"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union
from collections import defaultdict

import aiohttp
from aiohttp import ClientTimeout

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from urllib.parse import urlparse
from frappe.utils import get_request_site_address, now_datetime, add_to_date

from .doctype.doctype_names_mapping import (
    ROUTES_TABLE_CHILD_DOCTYPE_NAME,
    ROUTES_TABLE_DOCTYPE_NAME,
    SETTINGS_DOCTYPE_NAME,
    DIGITAX_ID_MAPPING_DOCTYPE_NAME,
)


def is_valid_kra_pin(pin: str) -> bool:
    """Checks if the string provided conforms to the pattern of a KRA PIN.
    This function does not validate if the PIN actually exists, only that
    it resembles a valid KRA PIN.

    Args:
        pin (str): The KRA PIN to test

    Returns:
        bool: True if input is a valid KRA PIN, False otherwise
    """
    pattern = r"^[a-zA-Z]{1}[0-9]{9}[a-zA-Z]{1}$"
    return bool(re.match(pattern, pin))


async def make_get_request(url: str) -> dict[str, str] | str:
    """Make an Asynchronous GET Request to specified URL

    Args:
        url (str): The URL

    Returns:
        dict: The Response
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.content_type.startswith("text"):
                return await response.text()

            return await response.json()


async def make_post_request(
    url: str,
    data: dict[str, str] | None = None,
    headers: dict[str, str | int] | None = None,
) -> dict[str, str | dict]:
    """Make an Asynchronous POST Request to specified URL

    Args:
        url (str): The URL
        data (dict[str, str] | None, optional): Data to send to server. Defaults to None.
        headers (dict[str, str | int] | None, optional): Headers to set. Defaults to None.

    Returns:
        dict: The Server Response
    """
    async with aiohttp.ClientSession(timeout=ClientTimeout(1800)) as session:
        async with session.post(url, json=data, headers=headers) as response:
            return await response.json()


def build_datetime_from_string(
    date_string: str, format: str = "%Y-%m-%d %H:%M:%S"
) -> datetime:
    """Builds a Datetime object from string, and format provided

    Args:
        date_string (str): The string to build object from
        format (str, optional): The format of the date_string string. Defaults to "%Y-%m-%d".

    Returns:
        datetime: The datetime object
    """
    date_object = datetime.strptime(date_string, format)

    return date_object


def is_valid_url(url: str) -> bool:
    """Validates input is a valid URL

    Args:
        input (str): The input to validate

    Returns:
        bool: Validation result
    """
    pattern = r"^(https?|ftp):\/\/[^\s/$.?#].[^\s]*"
    return bool(re.match(pattern, url))


def get_route_path(
    search_field: str,
    vendor: str = "Digitax",
    routes_table_doctype: str = ROUTES_TABLE_CHILD_DOCTYPE_NAME,
    parent_doctype: str = ROUTES_TABLE_DOCTYPE_NAME,
) -> tuple[str, str] | None:

    RoutesTable = DocType(routes_table_doctype)
    ParentTable = DocType(parent_doctype)

    query = (
        frappe.qb.from_(RoutesTable)
        .join(ParentTable)
        .on(RoutesTable.parent == ParentTable.name)
        .select(RoutesTable.url_path, RoutesTable.last_request_date)
        .where(
            (RoutesTable.url_path_function.like(search_field))
            & (ParentTable.vendor.like(vendor))
        )
        .limit(1)
    )

    results = query.run(as_dict=True)

    if results:
        return (results[0]["url_path"], results[0]["last_request_date"])

    return None, None


def get_server_url(
    company_name: str, branch_id: str = "00", settings_name: str = None
) -> str | None:
    settings = get_settings(company_name, branch_id, settings_name)

    if settings:
        server_url = settings.get("server_url")

        return server_url

    return


def build_headers(
    company_name: str, branch_id: str, settings_name: str = None
) -> dict[str, str] | None:
    """
    Build headers for Digitax API requests.
    Checks for token validity and refreshes the token if expired.

    Args:
        company_name (str): The name of the company.
        branch_id (str, optional): The branch ID. Defaults to "00".

    Returns:
        dict[str, str] | None: The headers including the refreshed token or None if failed.
    """
    settings = get_settings(company_name, branch_id, settings_name)
    settings_doc = (
        frappe.get_doc(SETTINGS_DOCTYPE_NAME, settings.get("name"))
        if settings
        else None
    )

    if settings_doc:
        api_key = settings_doc.get_password("api_key")

        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        return headers

    return None


def get_settings(
    company_name: str = None, branch_id: str = None, settings_name: str = None
) -> dict | None:
    """Fetch settings for a given company and branch.

    Args:
        company_name (str, optional): The name of the company. Defaults to None.
        branch_id (str, optional): The branch ID. Defaults to None.

    Returns:
        dict | None: The settings if found, otherwise None.
    """
    if settings_name:
        if frappe.db.exists(SETTINGS_DOCTYPE_NAME, {"name": settings_name}):
            return frappe.get_doc(SETTINGS_DOCTYPE_NAME, settings_name).as_dict()

    if frappe.db.exists(
        SETTINGS_DOCTYPE_NAME, {"company": company_name, "is_active": 1}
    ):
        mapping = frappe.db.get_value(
            SETTINGS_DOCTYPE_NAME,
            {"company": company_name, "is_active": 1},
            "name",
            as_dict=True,
        )
        if mapping and mapping.name:
            return frappe.get_doc(SETTINGS_DOCTYPE_NAME, mapping.name).as_dict()

    return None


def get_kes_conversion_rate(currency, company_currency, posting_date=None):
    """
    Resolve conversion to KES.

    Priority:
    1. currency -> KES
    2. company_currency -> KES

    Returns:
        (conversion_rate, used_rate)

    Throws:
        If no valid rate exists.
    """

    if not posting_date:
        posting_date = frappe.utils.nowdate()

    def get_rate(frm, to):
        return frappe.db.get_value(
            "Currency Exchange",
            {
                "from_currency": frm,
                "to_currency": to,
                "date": ["<=", posting_date],
                "for_selling": 1,
            },
            "exchange_rate",
            order_by="date desc",
        )

    rate = get_rate(currency, "KES")
    if rate:
        return rate, "net"

    rate = get_rate(company_currency, "KES")
    if rate:
        return rate, "base"
    frappe.throw(
        f"No exchange rate found to KES for {currency} or {company_currency} on {posting_date}"
    )


def build_invoice_payload(invoice: "Document", settings_name: str) -> dict:
    currency = invoice.currency
    company_currency = frappe.get_value("Company", invoice.company, "default_currency")

    convertion_rate = 1
    rate_field, tax_field = "net_rate", "tax_amount"

    if currency == "KES":
        rate_field = "net_rate"
        tax_field = "tax_amount"
    elif company_currency == "KES":
        rate_field = "base_net_rate"
        tax_field = "base_tax_amount"
    else:
        convertion_rate, used_rate = get_kes_conversion_rate(
            currency=currency,
            company_currency=company_currency,
            posting_date=invoice.posting_date,
        )
        if used_rate != "net":
            rate_field = "base_net_rate"
            tax_field = "base_tax_amount"

    date_str = f"{invoice.posting_date} {invoice.posting_time or '00:00:00'}"
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in date_str else "%Y-%m-%d %H:%M:%S"
    formatted_date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")

    reference_number = get_invoice_reference_number(invoice)

    payload = {
        "sale_date": formatted_date,
        "trader_invoice_number": reference_number,
        "receipt_type_code": "S",
        "payment_type_code": "07",
        "invoice_status_code": "01",
        "customer_tin": frappe.get_value("Customer", invoice.customer, "tax_id"),
        "customer_name": frappe.get_value(
            "Customer", invoice.customer, "customer_name"
        ),
        "customer_id": get_digitax_id("Customer", invoice.customer, settings_name),
        "invoice_details": invoice.remarks or f"Invoice {invoice.name}",
        "callback_url": build_callback_url(
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.apis.apis.invoice_submission_callback"
        ),
        "items": [],
        "document_name": invoice.name,
    }

    if hasattr(invoice, "is_tax_exempt"):
        payload["is_tax_exempt"] = bool(invoice.is_tax_exempt)

    tax_map = calculate_tax(invoice)

    for item in invoice.items:
        qty = abs(item.get("qty") or 0)
        if not qty:
            continue

        item_tax_data = tax_map.get(item.name, {})
        tax_amount = item_tax_data.get(tax_field, 0)
        tax_code = item_tax_data.get("taxation_type_code", "A")

        unit_net_price = item.get(rate_field) or 0
        unit_tax = tax_amount / qty
        unit_price_inclusive = round((unit_net_price + unit_tax) * convertion_rate, 4)
        total_amount = round(unit_price_inclusive * qty, 4)

        item_payload = {
            "id": get_digitax_id("Item", item.item_code, settings_name)
            or item.item_code,
            "item_description": item.item_name or item.item_code,
            "quantity": round(qty, 2),
            "unit_price": unit_price_inclusive,
            "total_amount": total_amount,
            "tax_code": tax_code,
            "uom": item.uom or "Pcs",
        }

        if item.get("package_unit_quantity"):
            item_payload["package_unit_quantity"] = item.get("package_unit_quantity")

        if item.get("discount_percentage"):
            item_payload["discount_rate"] = item.get("discount_percentage")

        if item.get("discount_amount"):
            item_payload["discount_amount"] = (
                item.get("discount_amount") * convertion_rate
            )

        payload["items"].append(item_payload)

    return payload


def update_last_request_date(
    response_datetime: str,
    route: str,
    routes_table: str = ROUTES_TABLE_CHILD_DOCTYPE_NAME,
) -> None:
    if len(route) < 5:
        return

    frappe.db.set_value(
        routes_table,
        {"url_path": route},
        "last_request_date",
        response_datetime,
        update_modified=False,
    )
    frappe.db.commit()


def calculate_tax(doc: Document) -> dict:
    """
    Orchestrates the tax calculation process by deciding between ERPNext's
    internal tax table or the custom hierarchical resolution engine.
    """
    tax_table = doc.get("item_wise_tax_details", [])

    if tax_table:
        return _calculate_from_item_wise_tax_table(doc, tax_table)

    return _calculate_taxes_by_hierarchy(doc)


def _calculate_taxes_by_hierarchy(doc: "Document") -> dict:
    """
    Resolves tax rates for each item using a hierarchical priority:
    1. Item Tax Template
    2. Document-level Sales Taxes and Charges Template
    3. Proportional distribution of manual tax entries
    """
    results = {}
    total_net = sum(float(i.base_net_amount or 0) for i in doc.items)
    template_rate = _get_sales_taxes_template_rate(doc.taxes_and_charges)
    has_item_templates = any(i.item_tax_template for i in doc.items)

    for item in doc.items:
        rate = 0.0
        base_net = float(item.base_net_amount or 0.0)

        if item.item_tax_template:
            rate = _get_item_tax_template_rate(item.item_tax_template)
        elif template_rate > 0:
            rate = template_rate
        elif not has_item_templates and doc.get("taxes") and total_net > 0:
            total_doc_tax = sum(float(t.tax_amount or 0) for t in doc.taxes)
            item_tax = total_doc_tax * (base_net / total_net)
            rate = (item_tax / base_net) * 100 if base_net else 0.0

        base_tax = (base_net * rate) / 100.0
        results[item.name] = _prepare_tax_entry(doc, item, base_tax, rate)

    return results


def _calculate_from_item_wise_tax_table(doc: "Document", tax_table: list) -> dict:
    """
    Aggregates tax data from the internal 'item_wise_tax_details' table
    to determine effective rates and amounts per item row.
    """
    results = {}
    grouped = defaultdict(lambda: {"tax": 0.0, "taxable": 0.0})

    for row in tax_table:
        grouped[row.item_row]["tax"] += float(row.amount or 0.0)
        grouped[row.item_row]["taxable"] = float(row.taxable_amount or 0.0)

    for item in doc.items:
        data = grouped.get(item.name)
        if not data:
            continue

        rate = (data["tax"] / data["taxable"]) * 100 if data["taxable"] else 0.0
        results[item.name] = _prepare_tax_entry(doc, item, data["tax"], rate)

    return results


def _prepare_tax_entry(
    doc: "Document", item: object, base_tax: float, rate: float
) -> dict:
    """
    Normalizes tax data by handling currency conversion logic and
    assigning the appropriate taxation type codes.
    """
    conv_rate = float(doc.get("conversion_rate", 1.0))
    is_foreign = doc.currency != frappe.get_cached_value(
        "Company", doc.company, "default_currency"
    )

    tax_amount = base_tax / conv_rate if is_foreign else base_tax

    return {
        "tax_amount": round(tax_amount, 2),
        "base_tax_amount": round(base_tax, 2),
        "tax_rate": round(rate, 2),
        "taxation_type_code": _determine_taxation_code(item, rate),
    }


def _get_sales_taxes_template_rate(template_name: str) -> float:
    """
    Fetches the total combined tax rate from a Sales Taxes and Charges Template.
    """
    if not template_name:
        return 0.0
    rates = frappe.get_all(
        "Sales Taxes and Charges", filters={"parent": template_name}, fields=["rate"]
    )
    return sum(float(r.rate or 0.0) for r in rates)


def _get_item_tax_template_rate(template_name: str) -> float:
    """
    Fetches the total combined tax rate from an Item Tax Template.
    """
    tax_template = frappe.get_doc("Item Tax Template", template_name)
    return (
        sum(float(tax.tax_rate or 0) for tax in tax_template.taxes)
        if tax_template.taxes
        else 0.0
    )


def _determine_taxation_code(item: object, rate: float) -> str:
    """
    Determines the taxation type code based on the Item Tax Template
    metadata or the calculated tax rate.
    """
    if item.item_tax_template:
        code = frappe.get_value(
            "Item Tax Template", item.item_tax_template, "etims_taxation_type"
        )
        if code:
            return code

    r = round(rate)
    if r >= 16:
        return "B"
    if r >= 8:
        return "E"
    if r == 0:
        return "A"
    return "A"


def apply_item_taxes_and_codes(doc: "Document") -> None:
    """
    Applies calculated tax data to the document items and persists
    the changes to the database.
    """
    tax_data_map = calculate_tax(doc)

    for item in doc.items:
        data = tax_data_map.get(item.name)
        if not data:
            continue

        item.tax_amount = data["tax_amount"]
        item.base_tax_amount = data["base_tax_amount"]
        item.tax_rate = data["tax_rate"]
        item.taxation_type_code = data["taxation_type_code"]

        frappe.db.set_value(
            "Sales Invoice Item",
            item.name,
            {
                "tax_amount": data["tax_amount"],
                "base_tax_amount": data["base_tax_amount"],
                "tax_rate": data["tax_rate"],
                "taxation_type_code": data["taxation_type_code"],
            },
            update_modified=False,
        )


def after_save_(doc: "Document", method: str | None = None) -> None:
    apply_item_taxes_and_codes(doc)


def get_invoice_number(invoice_name: str) -> int:
    """
    Extracts the numeric portion from the invoice naming series.

    Args:
        invoice_name (str): The name of the Sales Invoice document (e.g., 'eTIMS-INV-00-00001').

    Returns:
        int: The extracted invoice number.
    """
    parts = invoice_name.split("-")
    if len(parts) >= 3:
        return int(parts[-1])
    else:
        raise ValueError("Invoice name format is incorrect")


"""For cancelled and amended invoices"""


def clean_invc_no(invoice_name: str) -> str:
    if "-" in invoice_name:
        invoice_name = "-".join(invoice_name.split("-")[:-1])
    return invoice_name


def get_link_value(
    doctype: str, field_name: str, value: str, return_field: str = "name"
) -> str:
    try:
        return frappe.db.get_value(doctype, {field_name: value}, return_field)
    except Exception as e:
        frappe.log_error(
            title=f"Error Fetching Link for {doctype}",
            message=f"Error while fetching link for {doctype} with {field_name}={value}: {str(e)}",
        )
        return None


def get_or_create_link(doctype: str, field_name: str, value: str) -> str:
    if not value:
        return None

    try:
        link_name = frappe.db.get_value(doctype, {field_name: value}, "name")
        if not link_name:
            link_name = (
                frappe.get_doc(
                    {
                        "doctype": doctype,
                        field_name: value,
                        "code": value,
                    }
                )
                .insert(ignore_permissions=True, ignore_mandatory=True)
                .name
            )
            frappe.db.commit()
        return link_name
    except Exception as e:
        frappe.log_error(
            title=f"Error in get_or_create_link for {doctype}",
            message=f"Error in {doctype} - {value}: {str(e)}",
        )
        return None


def process_dynamic_url(route_path: str, request_data: dict | str) -> str:
    import json
    import re

    if isinstance(request_data, str):
        try:
            request_data = json.loads(request_data)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON string in request_data.") from e

    placeholders = re.findall(r"\{(.*?)\}", route_path)
    for placeholder in placeholders:
        if placeholder in request_data:
            route_path = route_path.replace(
                f"{{{placeholder}}}", str(request_data[placeholder])
            )
        else:
            raise ValueError(
                f"Missing required placeholder: '{placeholder}' in request_data."
            )

    return route_path


def parse_request_data(request_data: str | dict) -> dict:
    if isinstance(request_data, str):
        return json.loads(request_data)
    elif isinstance(request_data, (dict, list)):
        return request_data
    return {}


def get_max_submission_attempts(
    doctype: str = "Sales Invoice", company: str = None
) -> int:
    settings = get_settings(company_name=company)
    if not settings:
        return 3
    if doctype == "Sales Invoice":
        tries = settings.get("maximum_sales_information_submission_attempts", 3)
    elif doctype == "Purchase Invoice":
        tries = settings.get("maximum_purchase_information_submission_attempts", 3)
    elif doctype == "Stock Ledger Entry":
        tries = settings.get("maximum_stock_information_submission_attempts", 3)
    else:
        tries = 3
    return tries


@frappe.whitelist()
def get_active_settings(
    doctype: str = SETTINGS_DOCTYPE_NAME, company: str = None
) -> list[dict]:
    """
    Get active settings.
    If company is provided, return only active settings for that company.
    Otherwise, return all active settings.
    """
    try:
        filters = {"is_active": 1}
        if company:
            filters["company"] = company

        return (
            frappe.get_all(
                doctype,
                filters=filters,
                fields=["name", "company"],
                ignore_permissions=True,
            )
            or []
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), _("Failed to get active settings"))
        return []


def get_digitax_id(doctype: str, name: str, setting: str) -> str:
    if not frappe.db.exists(doctype, name):
        frappe.throw(
            _("Document {0} with name {1} does not exist.").format(doctype, name)
        )

    if not frappe.db.exists(SETTINGS_DOCTYPE_NAME, {"name": setting, "is_active": 1}):
        frappe.throw(_("eTims Setup {0} is not active.").format(setting))

    filters = {
        "etims_setup": setting,
        "parenttype": doctype,
        "parent": name,
    }

    mapping_meta = frappe.get_meta(DIGITAX_ID_MAPPING_DOCTYPE_NAME)

    if mapping_meta.has_field("is_active"):
        filters["is_active"] = 1

    if mapping_meta.has_field("disabled"):
        filters["disabled"] = 0

    return frappe.db.get_value(
        DIGITAX_ID_MAPPING_DOCTYPE_NAME,
        filters=filters,
        fieldname="digitax_id",
    )


def get_parent_by_digitax_id(doctype: str, digitax_id: str, setting: str) -> str:
    """Returns the parent document name for a given Digitax ID.

    Args:
        doctype (str): The parent doctype
        digitax_id (str): The Digitax ID to search for
        setting (str): The eTims setting name

    Returns:
        str: The parent document name if found, None otherwise
    """
    parent_name = frappe.db.get_value(
        DIGITAX_ID_MAPPING_DOCTYPE_NAME,
        filters={
            "etims_setup": setting,
            "parenttype": doctype,
            "digitax_id": digitax_id,
        },
        fieldname="parent",
    )

    return parent_name


@frappe.whitelist()
def get_etims_action_data(doctype: str, docname: str = None) -> dict[str, Any]:
    active_settings = get_active_settings()

    if not docname:
        return {
            "settings": active_settings,
            "has_mappings": False,
            "registered_mappings": [],
            "unregistered_settings": [],
        }
    try:
        doc = frappe.get_doc(doctype, docname)
    except:
        return {
            "settings": active_settings,
            "has_mappings": False,
            "registered_mappings": [],
            "unregistered_settings": [],
        }

    if not active_settings:
        return {
            "settings": [],
            "has_mappings": False,
            "registered_mappings": [],
            "unregistered_settings": [],
        }

    active_setting_names = [s["name"] for s in active_settings]

    registered_mappings = []
    registered_setup_names = set()

    for row in getattr(doc, "etims_setup_mapping", []):
        if row.etims_setup in active_setting_names:
            registered_mappings.append(
                {
                    "etims_setup": row.etims_setup,
                    "slade360_id": row.slade360_id,
                    "name": row.name,
                }
            )
            registered_setup_names.add(row.etims_setup)

    unregistered_settings = [
        s for s in active_settings if s["name"] not in registered_setup_names
    ]

    return {
        "settings": active_settings,
        "has_mappings": bool(registered_mappings),
        "registered_mappings": registered_mappings,
        "unregistered_settings": unregistered_settings,
    }


def parse_response_data(
    response: Union[str, bytes, dict, list], expected_type: type = list
) -> Union[List[Any], Dict[str, Any], Any]:
    """Parse and convert response data to expected type using standard json.

    Args:
        response: Input data (JSON string, bytes, or Python object)
        expected_type: Desired output type (list, dict, or other)

    Returns:
        Data converted to expected type

    Raises:
        ValueError: If JSON parsing fails
        TypeError: If type conversion fails
    """
    if isinstance(response, (str, bytes)):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}") from e

    if response is None:
        return expected_type()

    try:
        if expected_type is list:
            if isinstance(response, dict):
                return response.get("data", [response])
            return response if isinstance(response, list) else [response]

        elif expected_type is dict:
            if isinstance(response, list):
                return response[0] if response else {}
            return response if isinstance(response, dict) else {"data": response}

        return expected_type(response) if response else expected_type()

    except (TypeError, AttributeError) as e:
        raise TypeError(f"Cannot convert to {expected_type}: {str(e)}") from e


def build_item_payload(item) -> dict:
    """Construct the payload for item registration"""
    selling_price = round(item.get("valuation_rate", 1), 2) or 1

    stock_levels = frappe.db.get_all(
        "Bin",
        filters={"item_code": item.name},
        fields=["actual_qty"],
    )
    total_stock = sum(float(bin.actual_qty or 0) for bin in stock_levels)

    payload = {
        "document_name": item.name,
        "item_class_code": item.item_classification,
        "item_type_code": item.item_type,
        "item_name": item.item_name,
        "origin_nation_code": item.etims_country_of_origin_code,
        "package_unit_code": item.packaging_unit_code,
        "quantity_unit_code": item.unit_of_quantity_code,
        "tax_type_code": item.taxation_type,
        "default_unit_price": selling_price,
        "stock_quantity": total_stock,
        "callback_url": build_callback_url(
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.apis.apis.item_registration_callback"
        ),
    }

    return payload


def build_callback_url(endpoint: str) -> str:
    base_url = get_request_site_address(True)
    parsed_url = urlparse(base_url)

    if not (
        parsed_url.hostname == "localhost"
        or parsed_url.hostname.replace(".", "").isdigit()
    ):
        base_url = f"{parsed_url.scheme}://{parsed_url.hostname}"

    return f"{base_url}/api/method/{endpoint}"


def build_return_invoice_payload(
    invoice: Document, kra_invoice_data: Dict[str, Any], settings_name: str = None
) -> Dict[str, Any]:
    currency = invoice.currency
    company_currency = frappe.get_value("Company", invoice.company, "default_currency")
    convertion_rate = 1
    rate_field, tax_field = "net_rate", "tax_amount"

    if currency == "KES":
        rate_field = "net_rate"
        tax_field = "tax_amount"
    elif company_currency == "KES":
        rate_field = "base_net_rate"
        tax_field = "base_tax_amount"
    else:
        convertion_rate, _ = get_kes_conversion_rate(
            currency=currency,
            company_currency=company_currency,
            posting_date=invoice.posting_date,
        )
        rate_field = "base_net_rate"
        tax_field = "base_tax_amount"

    kra_total = sum(
        item.get("total_amount", 0) for item in kra_invoice_data.get("item_list", [])
    )
    return_total = abs(float(invoice.base_grand_total) * convertion_rate)

    is_full_return = abs(kra_total - return_total) < 0.01

    return prepare_return_invoice_payload(
        invoice=invoice,
        kra_invoice_data=kra_invoice_data,
        is_full_return=is_full_return,
        rate_field=rate_field,
        tax_field=tax_field,
        convertion_rate=convertion_rate,
        settings_name=settings_name,
    )


def get_invoice_reference_number(invoice: Document) -> str:
    """
    Generate a unique reference number for the invoice submission.

    - If the invoice has no revisions, the reference is simply the document name.
    - If the invoice has revisions (revision_count > 0), append `-REV{revision_count}`
      to make it unique and traceable (e.g., SINV-0001-REV1).

    Args:
        invoice (Document): The Invoice document instance.

    Returns:
        str: The generated reference number for submission.
    """
    reference_number = invoice.name
    if (
        hasattr(invoice, "revision_count")
        and invoice.revision_count is not None
        and int(invoice.revision_count) > 0
    ):
        reference_number = f"{invoice.name}-REV{int(invoice.revision_count)}"

    return reference_number


def prepare_return_invoice_payload(
    invoice: Document,
    kra_invoice_data: Dict[str, Any],
    is_full_return: bool,
    rate_field: str,
    tax_field: str,
    convertion_rate: float,
    settings_name: str = None,
) -> Dict[str, Any]:
    items = []

    if is_full_return:
        for line in kra_invoice_data.get("item_list", []):
            items.append(
                {
                    "id": line.get("item_id"),
                    "quantity": abs(line.get("quantity", 0)),
                    "unit_price": line.get("unit_price"),
                    "total_amount": abs(line.get("total_amount", 0)),
                    "item_description": line.get("etims_item_code"),
                }
            )
    else:
        for item in invoice.items:
            qty = abs(item.get("qty"))
            unit_price = (
                item.get(rate_field) + (item.get(tax_field) / item.get("qty", 1))
            ) * convertion_rate

            items.append(
                {
                    "id": get_digitax_id("Item", item.item_code, setting=settings_name)
                    or item.item_code,
                    "quantity": qty,
                    "unit_price": round(unit_price, 4),
                    "total_amount": round(unit_price * qty, 4),
                    "item_description": item.get("item_name"),
                }
            )

    return {
        "return_date": str(invoice.posting_date),
        "sale_id": kra_invoice_data.get("id"),
        "trader_invoice_number": invoice.name,
        "invoice_details": f"Return for {kra_invoice_data.get('trader_invoice_number')}",
        "items": items,
        "document_name": invoice.name,
    }


def validate_kra_pin(pin: str):
    if not pin:
        return

    pattern = r"^[A-Z]\d{9}[A-Z]$"

    if not re.match(pattern, pin):
        frappe.throw(
            _(
                "Invalid KRA PIN format. Expected format like P123456789H or A123456789B."
            )
        )


def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def get_next_run(frequency, cron=None):
    now = now_datetime()

    if not frequency:
        return None

    if frequency == "Hourly":
        return add_to_date(now, hours=1)
    elif frequency == "Daily":
        return add_to_date(now, days=1)
    elif frequency == "Weekly":
        return add_to_date(now, weeks=1)
    elif frequency == "Monthly":
        return add_to_date(now, months=1)
    elif frequency == "Cron" and cron:
        try:
            from croniter import croniter

            return croniter(cron, now).get_next(datetime)
        except ImportError:
            frappe.log_error(
                message="cron utility is not available", title="Missing Dependency"
            )
            return None

    return None
