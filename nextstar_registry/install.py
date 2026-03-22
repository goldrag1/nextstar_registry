import frappe
from nextstar_registry.nextstar_registry.data.seed import run as seed_registry


def after_install():
    seed_registry()


def after_uninstall():
    pass
