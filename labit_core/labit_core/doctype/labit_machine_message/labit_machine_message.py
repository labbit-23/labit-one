import frappe
from frappe.model.document import Document


class LabitMachineMessage(Document):

    def validate(self):
        if not self.is_new() and not frappe.has_permission("Labit Machine Message", "delete"):
            frappe.throw("Machine messages are immutable.")
