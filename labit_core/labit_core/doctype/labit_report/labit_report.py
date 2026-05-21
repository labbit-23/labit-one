import secrets

import frappe
from frappe.model.document import Document


class LabitReport(Document):

    def before_insert(self):
        if not self.qr_code_token:
            self.qr_code_token = secrets.token_hex(8)

    def validate(self):
        doc_before = self.get_doc_before_save()

        if self.status == "Approved":
            previous_status = doc_before.status if doc_before else None
            if previous_status != "Approved":
                self.approved_by = frappe.session.user
                self.approved_at = frappe.utils.now()

        if self.status == "Released":
            previous_status = doc_before.status if doc_before else None
            if previous_status != "Released":
                self.released_at = frappe.utils.now()

        if doc_before and doc_before.status == "Released" and self.status == "Draft":
            frappe.throw("A Released report cannot be moved back to Draft.")

    def on_update(self):
        doc_before = self.get_doc_before_save()
        previous_status = doc_before.status if doc_before else None
        if self.status == "Released" and previous_status != "Released":
            self._fire_release_webhook()

    def _fire_release_webhook(self):
        frappe.logger().info(f"Report {self.name} released — webhook stub")
