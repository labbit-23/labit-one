import frappe
from frappe.model.document import Document
from labit_core.utils.validators import validate_erpnext_link


class LabitRequisition(Document):

    def before_insert(self):
        self.created_by_user = frappe.session.user

    def validate(self):
        self._validate_references()
        self._validate_items()

    def _validate_references(self):
        # Principle 11: every ERPNext reference must be validated on save
        validate_erpnext_link("Patient", self.patient, "patient")
        if self.customer:
            validate_erpnext_link("Customer", self.customer, "customer")
        if self.sales_invoice:
            validate_erpnext_link("Sales Invoice", self.sales_invoice, "sales_invoice")
        if self.referred_by:
            validate_erpnext_link("Employee", self.referred_by, "referred_by")

    def _validate_items(self):
        if not self.items:
            frappe.throw("A requisition must have at least one test or package.")
        for row in self.items:
            validate_erpnext_link("Item", row.item, f"items row {row.idx}")

    def on_submit(self):
        pass  # placeholder for future workflow triggers

    def on_cancel(self):
        self.status = "Cancelled"
