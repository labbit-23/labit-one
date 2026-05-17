import frappe
from frappe import _


def validate_erpnext_link(doctype, value, field_label):
    """
    Validates that a linked ERPNext record exists.
    Raises hard error on save if the reference is orphaned.
    Implements Design Principle 11.
    """
    if not value:
        return
    if not frappe.db.exists(doctype, value):
        frappe.throw(
            _("Invalid reference: {0} '{1}' does not exist in {2}.").format(
                field_label, value, doctype
            )
        )
