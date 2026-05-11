import frappe
import frappe.defaults
from frappe import _

from ..apis.api_builder import EndpointsBuilder
from ..apis.process_request import process_request
from ..apis.remote_response_status_handlers import notices_search_on_success
from ..doctype.doctype_names_mapping import (
    SETTINGS_DOCTYPE_NAME,
)


endpoints_builder = EndpointsBuilder()


@frappe.whitelist()
def run_background_task(method_path: str, settings_name: str | None = None, request_data: dict | str | None = None) -> None:
    frappe.flags.ignore_permissions = True
    func = frappe.get_attr(method_path)
    return func(settings_name=settings_name, request_data=request_data)


@frappe.whitelist()
def refresh_notices(settings_name: str = None) -> None:
    if settings_name:
        try:
            perform_notice_search({}, settings_name)
        except Exception as e:
            frappe.log_error(
                f"Error performing notice search for {settings_name}: {str(e)}"
            )
    else:
        setups = frappe.get_all(
            SETTINGS_DOCTYPE_NAME,
            filters={"is_active": 1, "sandbox": 0},
            fields=["name"],
        )
        for setup in setups:
            current_settings = setup.name
            try:
                perform_notice_search({}, current_settings)
            except Exception as e:
                frappe.log_error(
                    f"Error performing notice search for {current_settings}: {str(e)}"
                )
                continue


@frappe.whitelist()
def perform_notice_search(request_data: str | dict, settings_name: str) -> str:
    """Function to perform notice search."""
    message = process_request(
        request_data,
        "NoticeSearchReq",
        notices_search_on_success,
        settings_name=settings_name,
    )
    return message
