app_name = "edevis"
app_title = "Edevis"
app_publisher = "phamos.eu"
app_description = "ERPNext Enhancement for Edevis"
app_email = "support@phamos.eu"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/edevis/css/edevis.css"
# app_include_js = "/assets/edevis/js/edevis.js"

# include js, css files in header of web template
# web_include_css = "/assets/edevis/css/edevis.css"
# web_include_js = "/assets/edevis/js/edevis.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "edevis/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Customer" : "public/js/customer.js",
    "Lead" : "public/js/lead.js",
    "Opportunity": "public/js/opportunity.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "edevis/public/icons.svg"

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

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "edevis.utils.jinja_methods",
# 	"filters": "edevis.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "edevis.install.before_install"
# after_install = "edevis.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "edevis.uninstall.before_uninstall"
# after_uninstall = "edevis.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "edevis.utils.before_app_install"
# after_app_install = "edevis.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "edevis.utils.before_app_uninstall"
# after_app_uninstall = "edevis.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "edevis.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
	"Opportunity": {
		"validate": "edevis.custom_scripts.custom_python.opportunity.fetch_lead"
	},

}

fixtures = [
    {"dt": "Translation", "filters": [
        [
            "name", "in", [
            "gjl90a7e63",
            "gitrkf1beu",
            "ggqc7oh1gj",
            "ggnbofjoaq",
            "gg0s7pu06s",
            "gb8n8pofv1",
            "gcnbiriisu",
            "gceik5povl",
            "gb1co6jil4",
            "gbhpvjqck1",
            "gaofstpch2"
            ]
        ]
    ]},
    {"dt": "Print Format", "filters": [
        [
            "name", "in", [
                "Quote",
                "QuoteNew",
                "QuoteTest",
                "Leistungsbeschreibung",
                "Auftragsbestätigung",
                "Invoice",
                "DeliveryNote"
              ]
        ]
    ]},
    {"dt": "Workflow", "filters": [
        [
            "name", "in", [
            "Lead Approval Process"
            ]
        ]
    ]},
    {
		"doctype": "Workflow State"
    },
    {"dt": "Role", "filters": [
        [
            "name", "in", [
            "00201 ADM",
            "00201 APP"
            ]
        ]
    ]},
     {"dt": "Client Script", "filters": [
        [
            "name", "in", [
            "Opportunity Validation",
            "Lead Validations"
            ]
        ]
    ]},
     {"dt": "Notification", "filters": [
        [
            "name", "in", [
            "Lead workflow",
            ]
        ]
    ]},
    {"dt": "Letter Head", "filters": [
        [
            "name", "in", [
                "edevis Letter",
                "edevis Datasheet",
                "edevis Datasheet Modern",
            ]
        ]
    ]}

]

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"edevis.tasks.all"
# 	],
# 	"daily": [
# 		"edevis.tasks.daily"
# 	],
# 	"hourly": [
# 		"edevis.tasks.hourly"
# 	],
# 	"weekly": [
# 		"edevis.tasks.weekly"
# 	],
# 	"monthly": [
# 		"edevis.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "edevis.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "edevis.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "edevis.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["edevis.utils.before_request"]
# after_request = ["edevis.utils.after_request"]

# Job Events
# ----------
# before_job = ["edevis.utils.before_job"]
# after_job = ["edevis.utils.after_job"]

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
# 	"edevis.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


jinja = {
    "methods": [
        "edevis.custom_scripts.custom_python.quote_methods.check_quoteitems",
        "edevis.custom_scripts.custom_python.quote_methods.has_custom_pos",
        "edevis.custom_scripts.custom_python.quote_methods.quote_checkpaymentterms",
        "edevis.custom_scripts.custom_python.quote_methods.quoteitem_is_header",
        "edevis.custom_scripts.custom_python.quote_methods.is_sectionend",
        "edevis.custom_scripts.custom_python.quote_methods.quoteitem_has_discount",
        "edevis.custom_scripts.custom_python.quote_methods.structurize_quoteitem"
    ]
}

