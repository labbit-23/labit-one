import frappe
from frappe.model.document import Document


class LabitTest(Document):

    def before_insert(self):
        if not self.item:
            self._create_item()

    def validate(self):
        self._validate_required_samples()

    def _create_item(self):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": self.test_code,
            "item_name": self.item_name or self.test_code,
            "item_group": frappe.db.get_single_value("Labit Settings", "default_test_item_group") or "Lab Tests",
            "is_sales_item": 1,
            "is_stock_item": 0,
            "is_purchase_item": 0,
            "description": f"Lab Test: {self.item_name or self.test_code}",
        })
        item.insert(ignore_permissions=True)
        self.item = item.name
        frappe.msgprint(f"ERPNext Item '{item.name}' created automatically.", alert=True)

    def _validate_required_samples(self):
        if not self.required_samples:
            frappe.throw(
                "At least one Required Sample must be specified for a test."
            )
