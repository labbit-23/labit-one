import frappe
from frappe.model.document import Document


class LabitPackage(Document):

    def before_insert(self):
        if not self.item:
            self._create_item()

    def validate(self):
        self._validate_tests()

    def _create_item(self):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": self.package_code,
            "item_name": self.item_name or self.package_code,
            "item_group": frappe.db.get_single_value("Labit Settings", "default_package_item_group") or "Lab Packages",
            "is_sales_item": 1,
            "is_stock_item": 0,
            "is_purchase_item": 0,
            "description": f"Lab Package: {self.item_name or self.package_code}",
        })
        item.insert(ignore_permissions=True)
        self.item = item.name
        frappe.msgprint(f"ERPNext Item '{item.name}' created automatically.", alert=True)

    def _validate_tests(self):
        if not self.tests:
            frappe.throw(
                "At least one Test must be added to the package."
            )
