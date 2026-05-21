import frappe
from frappe import _
from frappe.model.document import Document


class LabitInstrumentTestMap(Document):

    def validate(self):
        self._validate_unique_key()
        self._validate_parameter_belongs_to_test()

    def _validate_unique_key(self):
        filters = {
            "instrument_id": self.instrument_id,
            "machine_test_name": self.machine_test_name,
            "time_point_minutes": self.time_point_minutes or 0,
        }
        if self.sample_type:
            filters["sample_type"] = self.sample_type
        else:
            filters["sample_type"] = ["is", "not set"]

        existing = frappe.db.get_value("Labit Instrument Test Map", filters, "name")
        if existing and existing != self.name:
            frappe.throw(
                _(
                    "A mapping already exists for instrument {0}, test name '{1}', "
                    "sample type '{2}', time point {3} min (→ {4})."
                ).format(
                    self.instrument_id,
                    self.machine_test_name,
                    self.sample_type or "any",
                    self.time_point_minutes or 0,
                    existing,
                ),
                frappe.DuplicateEntryError,
            )

    def _validate_parameter_belongs_to_test(self):
        if not (self.labit_test and self.labit_parameter):
            return
        parent_test = frappe.db.get_value(
            "Labit Test Parameter Link",
            {"parameter": self.labit_parameter, "parent": self.labit_test},
            "parent",
        )
        if not parent_test:
            frappe.throw(
                _("Parameter '{0}' is not linked to test '{1}'.").format(
                    self.labit_parameter, self.labit_test
                )
            )
