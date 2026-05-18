import frappe
from frappe.model.document import Document


class LabitSampleEvent(Document):

    def on_trash(self):
        frappe.throw("Sample events cannot be deleted.")
