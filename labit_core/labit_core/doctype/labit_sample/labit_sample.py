import frappe
from frappe.model.document import Document
from labit_core.utils.validators import validate_erpnext_link


class LabitSample(Document):

    def before_insert(self):
        # barcode will be set after naming, handled in after_insert
        pass

    def after_insert(self):
        self.db_set("barcode", self.name)

    def validate(self):
        if self.patient:
            validate_erpnext_link("Patient", self.patient, "patient")
        if self.requisition:
            validate_erpnext_link("Labit Requisition", self.requisition, "requisition")
        if self.patient_identity_verified:
            if not self.verification_method:
                frappe.throw("Verification method is required when patient identity is marked as verified.")
            if not self.verified_by:
                frappe.throw("Verified by (Employee) is required when patient identity is marked as verified.")

    def on_update(self):
        # When requisition is linked, record who linked it and when
        if self.requisition and not self.linked_at:
            self.db_set("linked_by", frappe.session.user)
            self.db_set("linked_at", frappe.utils.now())
        self._write_sample_event()

    def _write_sample_event(self):
        # Write a sample event for status changes
        if self.has_value_changed("status"):
            frappe.get_doc({
                "doctype": "Labit Sample Event",
                "sample": self.name,
                "requisition": self.requisition,
                "event_type": self.status.lower().replace(" ", "_"),
                "actor": frappe.session.user,
                "timestamp": frappe.utils.now(),
                "payload": frappe.as_json({
                    "previous_status": self.get_doc_before_save().status if self.get_doc_before_save() else None,
                    "new_status": self.status
                })
            }).insert(ignore_permissions=True)
