import frappe
from frappe.model.document import Document


class LabitOrganizationProfile(Document):
    def validate(self):
        if self.org_type == "Government Scheme" and not self.scheme_code:
            frappe.throw("Scheme Code is required for Government Scheme organizations.")
