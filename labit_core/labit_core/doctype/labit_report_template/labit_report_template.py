import re

import frappe
from frappe.model.document import Document


class LabitReportTemplate(Document):

    def validate(self):
        if self.template_code and not re.match(r"^[A-Za-z0-9_]+$", self.template_code):
            frappe.throw(
                "Template Code must contain only alphanumeric characters and underscores."
            )
