from __future__ import annotations

from datetime import datetime
from typing import Callable, Literal, Optional, Union
from urllib import parse

import requests

import frappe
from frappe.integrations.utils import create_request_log
from frappe.model.document import Document

from ..logger import etims_logger
from ..utils import (
    update_last_request_date,
)
from .remote_response_status_handlers import on_digitax_error


class BaseEndpointsBuilder:
    """Abstract Endpoints Builder class"""

    def __init__(self) -> None:
        self.integration_request: str | Document | None = None
        self.error: str | Exception | None = None
        self._observers: list[ErrorObserver] = []
        self.doctype: str | Document | None = None
        self.document_name: str | None = None

    def attach(self, observer: ErrorObserver) -> None:
        """Attach an observer

        Args:
            observer (AbstractObserver): The observer to attach
        """
        self._observers.append(observer)

    def notify(self) -> None:
        """Notify all attached observers."""
        for observer in self._observers:
            observer.update(self)


class ErrorObserver:
    """Error observer class."""

    def update(self, notifier: BaseEndpointsBuilder) -> None:
        """Reacts to event from notifier

        Args:
            notifier (AbstractEndpointsBuilder): The event notifier object
        """
        if notifier.error:
            update_integration_request(
                notifier.integration_request.name,
                status="Failed",
                output=None,
                error=notifier.error,
            )
            etims_logger.exception(notifier.error, exc_info=True)
            frappe.log_error(
                title="Fatal Error",
                message=notifier.error,
                reference_doctype=notifier.doctype,
                reference_name=notifier.document_name,
            )
            frappe.throw(
                """A Fatal Error was Encountered.
                Please check the Error Log for more details""",
                notifier.error,
                title="Fatal Error",
            )


class EndpointsBuilder(BaseEndpointsBuilder):
    """
    Base Endpoints Builder class.
    This class harbours common functionalities when communicating with etims servers
    """

    def __init__(self) -> None:
        super().__init__()
        self._url: str | None = None
        self._route_path: str | None = None
        self._request_description: str | None = None
        self._payload: dict | None = None
        self._settings: dict | None = None
        self._headers: dict | None = None
        self._method: Literal["GET", "POST", "PATCH", "PUT"] | None = None
        self._success_callback_handler: Callable | None = None
        self._error_callback_handler: Callable | None = None

        self.attach(ErrorObserver())

    @property
    def method(self) -> Literal["GET", "POST", "PATCH", "PUT"] | None:
        """The HTTP method to use for the request."""
        return self._method

    @method.setter
    def method(self, new_method: Literal["GET", "POST", "PATCH", "PUT"]) -> None:
        self._method = new_method

    @property
    def url(self) -> str | None:
        return self._url

    @url.setter
    def url(self, new_url: str) -> None:
        self._url = new_url

    @property
    def route_path(self) -> str | None:
        return self._route_path

    @route_path.setter
    def route_path(self, new_route_path: str) -> None:
        self._route_path = new_route_path

    @property
    def request_description(self) -> str | None:
        return self._request_description

    @request_description.setter
    def request_description(self, new_request_description: str) -> None:
        self._request_description = new_request_description

    @property
    def payload(self) -> dict | None:
        return self._payload

    @payload.setter
    def payload(self, new_payload: dict) -> None:
        self._payload = new_payload

    @property
    def settings(self) -> dict | None:
        return self._settings

    @settings.setter
    def settings(self, new_settings: dict) -> None:
        self._settings = new_settings

    @property
    def headers(self) -> dict | None:
        return self._headers

    @headers.setter
    def headers(self, new_headers: dict) -> None:
        self._headers = new_headers

    @property
    def success_callback(self) -> Callable | None:
        return self._success_callback_handler

    @success_callback.setter
    def success_callback(self, callback: Callable) -> None:
        self._success_callback_handler = callback

    @property
    def error_callback(self) -> Callable | None:
        return self._error_callback_handler

    @error_callback.setter
    def error_callback(
        self,
        callback: Callable[[dict | str, str, str, str], None],
    ) -> None:
        self._error_callback_handler = callback

    def make_remote_call(
        self,
        doctype: Document | str | None = None,
        document_name: str | None = None,
        retrying: bool = False,
    ) -> str | None:
        """Handles communication to Digitax servers."""
        if (
            self._url is None
            or self._headers is None
            or self._method is None
            or self._success_callback_handler is None
        ):
            frappe.throw(
                """Please ensure all required parameters (URL, headers, method, success, and error callbacks) are set.""",
                frappe.MandatoryError,
                title="Setup Error",
                is_minimizable=True,
            )

        if not self._settings.is_active == 1:
            frappe.log_error(
                title="Inactive eTims Settings",
                message=f"eTims settings {self._settings.name} is inactive. Cannot make remote call.",
                reference_doctype=doctype,
                reference_name=document_name,
            )
            return

        self.doctype, self.document_name = doctype, document_name
        route_path = self._route_path
        current_int_req = None

        if not retrying:
            try:
                current_int_req = create_request_log(
                    data=self._payload,
                    request_description=self._request_description,
                    is_remote_request=True,
                    service_name=self._request_description,
                    request_headers=self._headers,
                    url=self._url,
                    reference_docname=document_name,
                    reference_doctype=doctype,
                )
            except Exception:
                current_int_req = create_request_log(
                    data=self._payload,
                    request_description=self._request_description,
                    is_remote_request=True,
                    service_name=self._request_description,
                    request_headers=self._headers,
                    url=self._url,
                    reference_doctype=doctype,
                )

        self.integration_request = current_int_req

        try:
            if self._method == "POST":
                response = requests.post(
                    self._url, json=self._payload, headers=self._headers
                )
            elif self._method == "GET":
                response = requests.get(
                    self._url, headers=self._headers, params=self._payload
                )

            elif self._method == "PATCH":
                patch_id = self._payload.pop("id", None)
                if patch_id and f"/{patch_id}/" not in self._url:
                    self._url = f"{self._url.rstrip('/')}/{patch_id}/"
                response = requests.patch(
                    self._url, json=self._payload, headers=self._headers
                )
            elif self._method == "PUT":
                put_id = self._payload.pop("id", None)
                if put_id and f"/{put_id}/" not in self._url:
                    self._url = f"{self._url.rstrip('/')}/{put_id}/"
                response = requests.put(
                    self._url, json=self._payload, headers=self._headers
                )

            response_data = get_response_data(response)
            update_last_request_date(datetime.now(), self._route_path)

            if response.status_code in {200, 201}:
                update_integration_request(
                    current_int_req.name,
                    status="Completed",
                    output=str(response_data),
                    error=None,
                )

                self._success_callback_handler(
                    response=response_data,
                    document_name=document_name,
                    doctype=doctype,
                    payload=self._payload,
                    settings_name=self._settings.name,
                    integration_request=current_int_req.name,
                )
            else:
                error_msg = str(response_data)
                update_integration_request(
                    current_int_req.name,
                    status="Failed",
                    output=str(response_data),
                    error=error_msg,
                )
                on_digitax_error(
                    response_data,
                    url=route_path,
                    doctype=doctype,
                    document_name=document_name,
                )

                if self._error_callback_handler:
                    self._error_callback_handler(
                        response=response_data,
                        url=route_path,
                        doctype=doctype,
                        document_name=document_name,
                        payload=self._payload,
                        settings_name=self._settings.name,
                    )

            return response_data

        except Exception as error:
            if current_int_req:
                update_integration_request(
                    current_int_req.name, status="Failed", error=str(error)
                )
            frappe.log_error(
                title="eTims Execution Error", message=frappe.get_traceback()
            )
            return None


def get_response_data(response: requests.Response) -> Optional[Union[dict, str, bytes]]:
    content_type = response.headers.get("Content-Type", "").lower()

    if "application/json" in content_type:
        return response.json()
    elif "text/plain" in content_type or "text/html" in content_type:
        return response.text if response.text.strip() else None
    elif "application/xml" in content_type or "text/xml" in content_type:
        return response.text if response.text.strip() else None
    elif (
        "application/octet-stream" in content_type
        or "application/pdf" in content_type
        or "application/zip" in content_type
    ):
        return response.content

    return None


def update_integration_request(
    integration_request: str,
    status: Literal["Completed", "Failed"],
    output: str | None = None,
    error: str | None = None,
    request_description: str | None = None,
) -> None:
    """Updates the given integration request record silently without creating a version.

    Args:
        integration_request (str): The provided integration request.
        status (Literal["Completed", "Failed"]): The new status of the request.
        output (str | None, optional): The response message, if any. Defaults to None.
        error (str | None, optional): The error message, if any. Defaults to None.
        request_description (str | None, optional): Additional description for the request.
    """
    update_fields = {"status": status}

    if error:
        current_error = frappe.db.get_value(
            "Integration Request", integration_request, "error"
        )
        if current_error == "null" or not current_error:
            update_fields["error"] = error[:5000] if len(error) > 5000 else error
        elif error not in current_error:
            new_error = current_error + "\n" + error
            update_fields["error"] = (
                new_error[:5000] if len(new_error) > 5000 else new_error
            )

    if output:
        current_output = frappe.db.get_value(
            "Integration Request", integration_request, "output"
        )
        if current_output == "null" or not current_output:
            update_fields["output"] = output[:5000] if len(output) > 5000 else output
        elif output not in current_output:
            new_output = current_output + "\n" + output
            update_fields["output"] = (
                new_output[:5000] if len(new_output) > 5000 else new_output
            )

    if request_description:
        current_desc = frappe.db.get_value(
            "Integration Request", integration_request, "request_description"
        )
        if current_desc == "null" or not current_desc:
            update_fields["request_description"] = (
                request_description[:5000]
                if len(request_description) > 5000
                else request_description
            )
        elif request_description not in current_desc:
            new_desc = current_desc + " - " + request_description
            update_fields["request_description"] = (
                new_desc[:5000] if len(new_desc) > 5000 else new_desc
            )

    frappe.db.set_value(
        "Integration Request", integration_request, update_fields, update_modified=False
    )
    frappe.db.commit()
