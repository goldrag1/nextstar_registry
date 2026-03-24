import frappe

no_cache = 1


def get_context(context):
    context.no_cache = 1
    # This makes the page accessible without login
    context.show_sidebar = False
