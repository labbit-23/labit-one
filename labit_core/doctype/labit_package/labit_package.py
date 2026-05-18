import frappe
from frappe.model.document import Document


class LabitPackage(Document):

    def validate(self):
        self._validate_tests()

    def _validate_tests(self):
        if not self.tests:
            frappe.throw(
                "At least one Test must be added to the package."
            )
