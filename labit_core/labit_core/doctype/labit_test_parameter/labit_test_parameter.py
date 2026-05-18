import frappe
from frappe.model.document import Document


class LabitTestParameter(Document):

    def validate(self):
        self._validate_calculated()
        self._validate_machine_generated()

    def _validate_calculated(self):
        if self.is_calculated and not self.formula_expression:
            frappe.throw(
                "Formula Expression is required when the parameter is marked as Calculated."
            )

    def _validate_machine_generated(self):
        if self.is_machine_generated and not self.sample_type:
            frappe.throw(
                "Sample Type is required when the parameter is marked as Machine Generated."
            )
        if self.is_machine_generated and self.is_calculated:
            frappe.msgprint(
                "Warning: this parameter is marked as both Machine Generated and Calculated. "
                "This is unusual — please verify the configuration.",
                title="Unusual Configuration",
                indicator="orange",
            )
