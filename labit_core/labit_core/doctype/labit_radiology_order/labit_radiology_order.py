import frappe
from frappe.model.document import Document


class LabitRadiologyOrder(Document):

    def validate(self):
        if self.has_value_changed("report_status") and self.report_status == "Approved":
            self.report_approved_at = frappe.utils.now()

    def on_update(self):
        if self.has_value_changed("report_status") and self.report_status == "Approved":
            frappe.logger().info(f"Radiology {self.name} approved — webhook stub")
