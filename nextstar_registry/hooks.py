app_name = "nextstar_registry"
app_title = "Nextstar Registry"
app_publisher = "Nextstar"
app_description = "Central registry API for Nextstar App Store"
app_email = "hello@nextstar-erp.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "nextstar_registry",
# 		"logo": "/assets/nextstar_registry/logo.png",
# 		"title": "Nextstar Registry",
# 		"route": "/nextstar_registry",
# 		"has_permission": "nextstar_registry.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/nextstar_registry/css/nextstar_registry.css"
# app_include_js = "/assets/nextstar_registry/js/nextstar_registry.js"

# include js, css files in header of web template
# web_include_css = "/assets/nextstar_registry/css/nextstar_registry.css"
# web_include_js = "/assets/nextstar_registry/js/nextstar_registry.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "nextstar_registry/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "nextstar_registry/public/icons.svg"

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
# 	"methods": "nextstar_registry.utils.jinja_methods",
# 	"filters": "nextstar_registry.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "nextstar_registry.install.before_install"
after_install = "nextstar_registry.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "nextstar_registry.uninstall.before_uninstall"
after_uninstall = "nextstar_registry.install.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "nextstar_registry.utils.before_app_install"
# after_app_install = "nextstar_registry.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "nextstar_registry.utils.before_app_uninstall"
# after_app_uninstall = "nextstar_registry.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "nextstar_registry.notifications.get_notification_config"

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

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"nextstar_registry.nextstar_registry.tasks.aggregate_health_data",
		"nextstar_registry.nextstar_registry.tasks.cleanup_old_health_reports",
		"nextstar_registry.nextstar_registry.tasks.expire_featured_listings",
		"nextstar_registry.nextstar_registry.tasks.check_app_integrity",
	],
	"monthly_long": [
		"nextstar_registry.nextstar_registry.tasks.calculate_monthly_payouts",
	],
}

# Testing
# -------

# before_tests = "nextstar_registry.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "nextstar_registry.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "nextstar_registry.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "nextstar_registry.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["nextstar_registry.utils.before_request"]
# after_request = ["nextstar_registry.utils.after_request"]

# Job Events
# ----------
# before_job = ["nextstar_registry.utils.before_job"]
# after_job = ["nextstar_registry.utils.after_job"]

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
# 	"nextstar_registry.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

