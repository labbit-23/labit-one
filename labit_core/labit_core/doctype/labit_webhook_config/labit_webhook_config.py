import frappe
from frappe.model.document import Document


class LabitWebhookConfig(Document):

    def validate(self):
        if not (self.url or "").startswith(("http://", "https://")):
            frappe.throw("Endpoint URL must start with http:// or https://")

        timeout = self.timeout_seconds or 0
        if not (1 <= timeout <= 60):
            frappe.throw("Timeout must be between 1 and 60 seconds.")
