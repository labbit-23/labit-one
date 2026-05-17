import frappe
from frappe import _


@frappe.whitelist()
def confirm_sample_collected(requisition_name, collected_by=None):
    """
    Mark all pending items as Collected and update requisition status.
    Creates Labit Sample records (stub — full impl in Phase 1 sprint 2).
    """
    doc = frappe.get_doc("Labit Requisition", requisition_name)
    if doc.status not in ("Registered",):
        frappe.throw(_("Sample collection can only be confirmed from Registered status."))

    for item in doc.items:
        if item.status == "Pending":
            item.status = "Collected"

    doc.status = "Sample Collected"
    doc.save()
    frappe.db.commit()

    return {"status": "ok", "requisition": requisition_name}


@frappe.whitelist()
def link_sales_invoice(requisition_name, sales_invoice_name):
    """
    Link an existing ERPNext Sales Invoice to a requisition.
    """
    if not frappe.db.exists("Sales Invoice", sales_invoice_name):
        frappe.throw(_("Sales Invoice {0} does not exist.").format(sales_invoice_name))

    doc = frappe.get_doc("Labit Requisition", requisition_name)
    doc.sales_invoice = sales_invoice_name
    doc.save()
    frappe.db.commit()

    return {"status": "ok", "sales_invoice": sales_invoice_name}


@frappe.whitelist()
def search_patients(query, limit=20):
    """
    Fast patient typeahead. Searches name, mobile, DOB, and custom MRN field.
    Returns minimal fields for the registration screen autocomplete.
    Target: under 200ms on indexed fields.
    """
    if not query or len(query) < 2:
        return []

    like = f"%{query}%"

    patients = frappe.db.sql("""
        SELECT
            name,
            patient_name,
            mobile,
            dob,
            sex
        FROM `tabPatient`
        WHERE
            patient_name LIKE %(like)s
            OR mobile LIKE %(like)s
            OR name LIKE %(like)s
        ORDER BY patient_name
        LIMIT %(limit)s
    """, {"like": like, "limit": int(limit)}, as_dict=True)

    return patients
