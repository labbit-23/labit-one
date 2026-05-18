import frappe
from frappe.model.document import Document


class LabitTest(Document):

    def validate(self):
        self._validate_required_samples()

    def _validate_required_samples(self):
        if not self.required_samples:
            frappe.throw(
                "At least one Required Sample must be specified for a test."
            )
