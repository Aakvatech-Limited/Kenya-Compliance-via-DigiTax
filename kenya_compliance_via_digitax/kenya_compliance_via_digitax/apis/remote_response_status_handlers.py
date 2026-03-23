from datetime import datetime
from io import BytesIO

import frappe
import qrcode

from ..doctype.doctype_names_mapping import (
    COUNTRIES_DOCTYPE_NAME,
    ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
    NOTICES_DOCTYPE_NAME,
    PACKAGING_UNIT_DOCTYPE_NAME,
    SETTINGS_DOCTYPE_NAME,
    DIGITAX_ID_MAPPING_DOCTYPE_NAME,
    TAXATION_TYPE_DOCTYPE_NAME,
    UNIT_OF_QUANTITY_DOCTYPE_NAME,
)
from ..handlers import handle_digitax_errors
from ..utils import (
    get_link_value,
    get_parent_by_digitax_id,
    parse_response_data,
)


def on_digitax_error(
    response: dict | str,
    url: str | None = None,
    doctype: str | None = None,
    document_name: str | None = None,
) -> None:
    """Base "on-error" callback.on_digitax_error

    Args:
        response (dict | str): The remote response
        url (str | None, optional): The remote address. Defaults to None.
        doctype (str | None, optional): The doctype calling the remote address. Defaults to None.
        document_name (str | None, optional): The document calling the remote address. Defaults to None.
        integration_reqeust_name (str | None, optional): The created Integration Request document name. Defaults to None.
    """
    handle_digitax_errors(
        response,
        route=url,
        doctype=doctype,
        document_name=document_name,
    )


"""
These functions are required as serialising lambda expressions is a bit involving.
"""


def update_document_mapping(
    doc_type: str, document_name: str, settings_name: str, digitax_id: str
) -> None:
    """Common function to update document mapping with Digitax IDs

    Args:
        doc_type (str): The document type to update
        document_name (str): The name of the document to update
        settings_name (str): The name of the eTims settings
        digitax_id (str): The Digitax ID to set
    """
    doc = frappe.get_doc(doc_type, document_name)
    found = False
    for row in doc.get("etims_setup_mapping", []):
        if row.etims_setup == settings_name:
            frappe.db.set_value(
                DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                row.name,
                {
                    "digitax_id": digitax_id,
                },
            )
            found = True
            break

    if not found:
        doc.append(
            "etims_setup_mapping",
            {
                "etims_setup": settings_name,
                "digitax_id": digitax_id,
            },
        )
        doc.save(ignore_permissions=True)

    return doc


def item_registration_on_success(
    response: dict, document_name: str, settings_name: str, **kwargs
) -> None:
    if not response:
        return

    digitax_id = response.get("id")
    if not digitax_id:
        return

    mapping_name = frappe.db.get_value(
        DIGITAX_ID_MAPPING_DOCTYPE_NAME,
        {
            "parent": document_name,
            "parenttype": "Item",
            "etims_setup": settings_name,
        },
        "name",
    )

    if mapping_name:
        frappe.db.set_value(
            DIGITAX_ID_MAPPING_DOCTYPE_NAME,
            mapping_name,
            {
                "etims_setup": settings_name,
                "company": frappe.db.get_value(
                    SETTINGS_DOCTYPE_NAME, settings_name, "company"
                ),
                "digitax_id": digitax_id,
                "disabled": 0,
            },
        )
    else:
        frappe.get_doc(
            {
                "doctype": DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                "parent": document_name,
                "parenttype": "Item",
                "parentfield": "digitax_id_mapping",
                "etims_setup": settings_name,
                "company": frappe.db.get_value(
                    SETTINGS_DOCTYPE_NAME, settings_name, "company"
                ),
                "digitax_id": digitax_id,
                "disabled": 0,
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def customer_details_submission_on_success(
    response: dict, document_name: str, settings_name: str, **kwargs
) -> None:
    digitax_id = response.get("id")
    if not digitax_id:
        return

    mapping_name = frappe.db.get_value(
        DIGITAX_ID_MAPPING_DOCTYPE_NAME,
        {
            "parent": document_name,
            "parenttype": "Customer",
            "etims_setup": settings_name,
        },
        "name",
    )

    if mapping_name:
        frappe.db.set_value(
            DIGITAX_ID_MAPPING_DOCTYPE_NAME,
            mapping_name,
            {
                "etims_setup": settings_name,
                "company": frappe.db.get_value(
                    SETTINGS_DOCTYPE_NAME, settings_name, "company"
                ),
                "digitax_id": digitax_id,
                "disabled": 0,
            },
        )
    else:
        frappe.get_doc(
            {
                "doctype": DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                "parent": document_name,
                "parenttype": "Customer",
                "parentfield": "digitax_id_mapping",
                "etims_setup": settings_name,
                "company": frappe.db.get_value(
                    SETTINGS_DOCTYPE_NAME, settings_name, "company"
                ),
                "digitax_id": digitax_id,
                "disabled": 0,
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def customer_details_submission_on_error(
    response: dict, document_name: str, settings_name: str, **kwargs
) -> None:
    message = response.get("message")
    if message and "customer already exists" in message:
        pass


def sales_information_submission_on_success(
    response: dict, document_name: str, doctype: str, settings_name: str, **kwargs
) -> None:
    """
    Callback after successful submission. Maps SCU data and signature_link.
    """
    updates = {
        "successfully_submitted": 1,
    }
    if response.get("id") or response.get("existing_sale_id"):
        updates["digitax_id"] = response.get("id") or response.get("existing_sale_id")

    frappe.db.set_value(doctype, document_name, updates)


def sales_information_submission_on_error(
    response: dict, document_name: str, doctype: str, settings_name: str, **kwargs
) -> None:
    updates = {
        "successfully_submitted": 1,
    }
    data = get_response_data(response)
    if data.get("id") or data.get("existing_sale_id"):
        name = data.get("trader_invoice_number")
        updates["digitax_id"] = data.get("id") or data.get("existing_sale_id")
        frappe.db.set_value(doctype, name, updates)


def update_invoice_info(
    response: dict,
    document_name: str,
    doctype: str,
    settings_name: str | None = None,
    **kwargs,
) -> None:
    process_invoice_response(response, document_name, doctype)


def process_invoice_response(
    response: dict, document_name: str = None, doctype: str = "Sales Invoice"
) -> None:
    """Common function to process invoice response and update document"""
    data = get_response_data(response)
    invoice_name = data.get("trader_invoice_number")
    if not invoice_name:
        return

    if not frappe.db.exists("Sales Invoice", invoice_name):
        frappe.log_error(
            title="Invoice Not Found During Callback",
            message=f"Invoice {invoice_name} not found.",
        )
        return

    image_url = (
        generate_and_attach_qr_code(data.get("etims_url"), invoice_name, doctype)
        if data.get("etims_url")
        else None
    )

    update_fields = {
        "digitax_id": data.get("id"),
        "etims_serial_number": data.get("serial_number"),
        "current_receipt_number": data.get("receipt_number"),
        "receipt_signature": data.get("receipt_signature"),
        "qr_code_url": data.get("etims_url"),
        "qr_code_data": image_url,
        "internal_data": data.get("internal_data"),
    }

    update_fields = {k: v for k, v in update_fields.items() if v is not None}

    frappe.db.set_value(
        "Sales Invoice",
        invoice_name,
        update_fields,
        update_modified=False,
    )

    frappe.db.commit()
    frappe.publish_realtime("refresh_form", invoice_name)


def verify_and_fix_invoice_info(
    response: dict,
    document_name: str,
    doctype: str,
    settings_name: str | None = None,
    **kwargs,
) -> None:
    pass


def get_response_data(response: dict) -> dict | None:
    """Extract data from response object, preferring data field over metadata"""
    if response.get("data") is not None:
        return response.get("data")[0] if response.get("data") else None
    if response.get("metadata") is not None:
        return response.get("metadata")
    return response


def generate_and_attach_qr_code(url: str, docname: str, doctype: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"QR-{docname}.png",
            "is_private": 0,
            "content": buffer.read(),
            "attached_to_doctype": doctype,
            "attached_to_name": docname,
        }
    )
    file_doc.save(ignore_permissions=True)

    return file_doc.file_url


def map_scu_fields(data: dict, docname: str, doctype: str, qr_key: str) -> dict:
    qr_url = data.get(qr_key)
    image_url = (
        generate_and_attach_qr_code(qr_url, docname, doctype) if qr_url else None
    )

    return {
        "qr_code_url": qr_url,
        "qr_code": image_url,
        "current_receipt_number": data.get("scu_receipt_number"),
        "control_unit_date_time": parse_datetime(data.get("scu_receipt_timestamp")),
        "receipt_signature": data.get("scu_receipt_signature"),
        "internal_data": data.get("scu_internal_data"),
        "scu_id": data.get("scu_id"),
        "scu_mrc_no": data.get("scu_mrc_number"),
        "scu_invoice_number": data.get("scu_invoice_number"),
    }


def parse_datetime(date_str: str, format: str = "%Y-%m-%dT%H:%M:%S%z") -> str:
    if not date_str:
        return
    try:
        if "T" in date_str:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        else:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def notices_search_on_success(response: dict | list, **kwargs) -> None:
    notices = response if isinstance(response, list) else response.get("data")
    if isinstance(notices, list):
        for notice in notices:
            create_notice_if_new(notice)
    else:
        frappe.log_error(
            title="Invalid Response Format",
            message="Expected a list or single notice in the response",
        )


def create_notice_if_new(notice: dict) -> None:
    exists = frappe.db.exists(
        NOTICES_DOCTYPE_NAME, {"notice_number": notice.get("notice_number")}
    )
    if exists:
        return

    raw_date = notice.get("registration_date")
    formatted_date = None

    if isinstance(raw_date, str):
        try:
            formatted_date = datetime.fromisoformat(raw_date).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, TypeError):
            pass

    doc = frappe.new_doc(NOTICES_DOCTYPE_NAME)
    doc.flags.ignore_permissions = True
    doc.flags.ignore_validate_update_after_submit = True
    doc.update(
        {
            "notice_number": notice.get("notice_number"),
            "title": notice.get("title"),
            "registration_name": notice.get("registration_name"),
            "details_url": notice.get("detail_url"),
            "registration_datetime": formatted_date,
            "contents": notice.get("content"),
        }
    )

    try:
        doc.insert()
        doc.submit()
    except frappe.exceptions.DuplicateEntryError:
        frappe.log_error(
            title="Duplicate Entry Error",
            message=f"Duplicate notice detected: {notice.get('notice_number')}",
        )
    except Exception:
        frappe.log_error(
            title="Notice Creation Failed",
            message=f"Error creating notice {notice.get('notice_number')}: {frappe.get_traceback()}",
        )


def parse_date(date_str: str) -> None:
    formats = [
        "%d%m%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y.%m.%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    if date_str.isdigit():
        try:
            return datetime.fromtimestamp(int(date_str))
        except ValueError:
            pass
    raise ValueError(f"Invalid date format: {date_str}")


def item_search_on_success(response: dict, settings_name: str, **kwargs) -> None:
    items = parse_response_data(response, list)
    for item_data in items:
        try:
            digitax_id = item_data.get("id")
            existing_item = frappe.db.get_value(
                DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                {"digitax_id": digitax_id, "etims_setup": settings_name},
                "parent",
                order_by="creation desc",
            )
            country_of_origin_code = (
                item_data.get("country_of_origin")[:2]
                if item_data.get("country_of_origin")
                else "ke"
            )
            country_of_origin = get_link_value(
                COUNTRIES_DOCTYPE_NAME, "code", country_of_origin_code
            )

            if existing_item:
                item_doc = frappe.get_doc("Item", existing_item)

            request_data = {
                "item_name": item_data.get("description", "Unknown Item"),
                "item_code": item_data.get("code", ""),
                "description": item_data.get("description", ""),
                "is_sales_item": item_data.get("can_be_sold", False),
                "is_purchase_item": item_data.get("can_be_purchased", False),
                "item_code_etims": item_data.get("scu_item_code", ""),
                "etims_country_of_origin_code": country_of_origin_code or "",
                "valuation_rate": round(item_data.get("selling_price", 0.0), 2),
                "last_purchase_rate": round(item_data.get("purchasing_price", 0.0), 2),
                "etims_country_of_origin": country_of_origin or "",
                "item_type": item_data.get("item_type", ""),
                "product_type": item_data.get("product_type", ""),
            }

            if item_data.get("scu_item_classification"):
                request_data["item_classification"] = get_parent_by_digitax_id(
                    ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
                    item_data.get("scu_item_classification"),
                    settings_name,
                )

            if item_data.get("packaging_unit"):
                request_data["packaging_unit"] = get_parent_by_digitax_id(
                    PACKAGING_UNIT_DOCTYPE_NAME,
                    item_data.get("packaging_unit"),
                    settings_name,
                )

            if item_data.get("quantity_unit"):
                request_data["unit_of_quantity"] = get_parent_by_digitax_id(
                    UNIT_OF_QUANTITY_DOCTYPE_NAME,
                    item_data.get("quantity_unit"),
                    settings_name,
                )

            if item_data.get("sale_taxes") and len(item_data.get("sale_taxes", [])) > 0:
                request_data["taxation_type"] = get_parent_by_digitax_id(
                    TAXATION_TYPE_DOCTYPE_NAME,
                    item_data.get("sale_taxes")[0],
                    settings_name,
                )

            if existing_item:
                item_doc = frappe.get_doc("Item", existing_item)
                item_doc.update(request_data)
                item_doc.flags.ignore_mandatory = True
                item_doc.save(ignore_permissions=True)
            else:
                request_data["item_group"] = (
                    frappe.db.get_value("Item Group", {"is_group": 1}, "name")
                    or "All Item Groups"
                )
                item_doc = frappe.get_doc({"doctype": "Item", **request_data})
                item_doc.flags.ignore_mandatory = True
                item_doc.insert(
                    ignore_permissions=True,
                    ignore_mandatory=True,
                    ignore_if_duplicate=True,
                )

            existing_mapping = frappe.db.exists(
                DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                {
                    "parent": item_doc.name,
                    "parenttype": "Item",
                    "parentfield": "etims_setup_mapping",
                    "etims_setup": settings_name,
                },
            )

            if existing_mapping:
                frappe.db.set_value(
                    DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                    existing_mapping,
                    {"digitax_id": digitax_id},
                )
            else:
                frappe.get_doc(
                    {
                        "doctype": DIGITAX_ID_MAPPING_DOCTYPE_NAME,
                        "parent": item_doc.name,
                        "parenttype": "Item",
                        "parentfield": "etims_setup_mapping",
                        "digitax_id": digitax_id,
                        "etims_setup": settings_name,
                    }
                ).insert(ignore_permissions=True)

        except Exception as e:
            frappe.log_error(
                title="Item Search Error",
                message=f"Error processing item {item_data.get('code')}: {str(e)}",
            )
            continue

    frappe.db.commit()


def initialize_device_submission_on_success(response: dict, **kwargs) -> None:
    pass


def customers_search_on_success(response: dict, **kwargs) -> None:
    data = response.get("data", []) if response.get("data") else response
    if isinstance(data, dict):
        data = [data]
    for customer in data:
        existing_customer = frappe.db.exists("Customer", {"digitax_id": customer["id"]})
        data = {
            "email_id": customer["email_address"],
            "mobile_no": customer["phone_number"],
            "tax_id": customer.get("customer_tax_pin"),
            "currency": customer.get("currency"),
            "active": 1 if customer.get("active") else 0,
            "customer_type": (
                customer.get("customer_type").title()
                if customer.get("customer_type")
                in ["Company", "Individual", "Partnership"]
                else "Individual"
            ),
        }

        if existing_customer and customer.get("is_customer"):
            doc = frappe.get_doc("Customer", existing_customer)
            doc.update(data)
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.new_doc("Customer")
            doc.update(data)
            doc.insert(ignore_permissions=True)
        frappe.db.commit()
