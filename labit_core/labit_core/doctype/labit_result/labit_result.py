import frappe
from frappe.model.document import Document


class LabitResult(Document):

    def before_insert(self):
        self.entered_by = frappe.session.user
        self.entered_at = frappe.utils.now()

    def validate(self):
        self._validate_sample_requisition_consistency()
        self._handle_verification()

    def _validate_sample_requisition_consistency(self):
        if self.sample and self.requisition:
            sample_requisition = frappe.db.get_value("Labit Sample", self.sample, "requisition")
            if sample_requisition and sample_requisition != self.requisition:
                frappe.throw(
                    "Sample {0} belongs to requisition {1}, not {2}.".format(
                        self.sample, sample_requisition, self.requisition
                    )
                )

    def _handle_verification(self):
        if self.has_value_changed("status") and self.status == "Verified":
            if not self.verified_by:
                self.verified_by = frappe.session.user
            if not self.verified_at:
                self.verified_at = frappe.utils.now()
