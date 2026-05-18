import frappe
from frappe.model.document import Document


class LabitBarcodeBatch(Document):

    def before_insert(self):
        self.issued_by = frappe.session.user

    def validate(self):
        if self.status == "Issued" and self.issued_count <= 0:
            frappe.throw("Issued Count must be greater than 0 when status is Issued.")
