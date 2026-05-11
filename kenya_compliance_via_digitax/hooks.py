app_name = "kenya_compliance_via_digitax"
app_title = "Kenya Compliance Via DigiTax"
app_publisher = "Navari LTD"
app_description = "About This app works to integrate ERPNext with KRA's eTIMS via DigiTax to allow for the sharing of information with the revenue authority."
app_email = "support@navari.co.ke"
app_license = "agpl-3.0"


# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "kenya_compliance_via_digitax",
# 		"logo": "/assets/kenya_compliance_via_digitax/logo.png",
# 		"title": "Kenya Compliance Via DigiTax",
# 		"route": "/kenya_compliance_via_digitax",
# 		"has_permission": "kenya_compliance_via_digitax.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kenya_compliance_via_digitax/css/kenya_compliance_via_digitax.css"
# app_include_js = "/assets/kenya_compliance_via_digitax/js/kenya_compliance_via_digitax.js"

# include js, css files in header of web template
# web_include_css = "/assets/kenya_compliance_via_digitax/css/kenya_compliance_via_digitax.css"
# web_include_js = "/assets/kenya_compliance_via_digitax/js/kenya_compliance_via_digitax.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kenya_compliance_via_digitax/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice": "kenya_compliance_via_digitax/overrides/client/sales_invoice.js",
    "Customer": "kenya_compliance_via_digitax/overrides/client/customer.js",
    "Item": "kenya_compliance_via_digitax/overrides/client/items.js",
    "Stock Ledger Entry": "kenya_compliance_via_digitax/overrides/client/stock_ledger_entry.js",
}

doctype_list_js = {
    "Item": "kenya_compliance_via_digitax/overrides/client/items_list.js",
    "Sales Invoice": "kenya_compliance_via_digitax/overrides/client/sales_invoice_list.js",
    "Customer": "kenya_compliance_via_digitax/overrides/client/customer_list.js",
}

# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "kenya_compliance_via_digitax/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "kenya_compliance_via_digitax.utils.jinja_methods",
# 	"filters": "kenya_compliance_via_digitax.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "kenya_compliance_via_digitax.install.before_install"
# after_install = "kenya_compliance_via_digitax.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "kenya_compliance_via_digitax.uninstall.before_uninstall"
# after_uninstall = "kenya_compliance_via_digitax.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "kenya_compliance_via_digitax.utils.before_app_install"
# after_app_install = "kenya_compliance_via_digitax.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "kenya_compliance_via_digitax.utils.before_app_uninstall"
# after_app_uninstall = "kenya_compliance_via_digitax.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kenya_compliance_via_digitax.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events


doc_events = {
    # 	"*": {
    # 		"on_update": "method",
    # 		"on_cancel": "method",
    # 		"on_trash": "method"
    # 	}
    "Sales Invoice": {
        "on_update": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.utils.after_save_"
        ],
        "on_submit": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.sales_invoice.on_submit"
        ],
        "validate": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.shared_overrides.validate"
        ],
        "before_cancel": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.sales_invoice.before_cancel"
        ],
        "on_update_after_submit": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.utils.after_save_"
        ],
    },
    "Item": {
        "validate": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.item.validate"
        ],
        "on_update": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.item.on_update"
        ],
        "on_trash": "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.item.prevent_item_deletion",
    },
    "Customer": {
        "after_save": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.customer.after_save"
        ],
        "validate": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.customer.validate"
        ],
        "after_insert": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.customer.after_insert"
        ],
    },
    "Stock Ledger Entry": {
        "on_submit": [
            "kenya_compliance_via_digitax.kenya_compliance_via_digitax.overrides.server.stock_ledger_entry.on_submit"
        ]
    },
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"kenya_compliance_via_digitax.tasks.all"
# 	],
# 	"daily": [
# 		"kenya_compliance_via_digitax.tasks.daily"
# 	],
# 	"hourly": [
# 		"kenya_compliance_via_digitax.tasks.hourly"
# 	],
# 	"weekly": [
# 		"kenya_compliance_via_digitax.tasks.weekly"
# 	],
# 	"monthly": [
# 		"kenya_compliance_via_digitax.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "kenya_compliance_via_digitax.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "kenya_compliance_via_digitax.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "kenya_compliance_via_digitax.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "kenya_compliance_via_digitax.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["kenya_compliance_via_digitax.utils.before_request"]
# after_request = ["kenya_compliance_via_digitax.utils.after_request"]

# Job Events
# ----------
# before_job = ["kenya_compliance_via_digitax.utils.before_job"]
# after_job = ["kenya_compliance_via_digitax.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"kenya_compliance_via_digitax.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
# Not required for frappe 15 because it is frappe v16 based
# require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


fixtures = [{"doctype": "eTims Routes"}]
