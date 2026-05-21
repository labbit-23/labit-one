import frappe


def _normalize_sex(value):
    """Map ERPNext sex values to DICOM single-character codes (M/F/O)."""
    v = str(value or "").strip().upper()
    if v in ("M", "MALE"):
        return "M"
    if v in ("F", "FEMALE"):
        return "F"
    return "O"


def _dicom_date(value):
    """Convert a date value (YYYY-MM-DD or date object) to DICOM YYYYMMDD string."""
    text = str(value or "").strip()
    if not text or text == "None":
        return ""
    # Already YYYYMMDD
    if len(text) == 8 and text.isdigit():
        return text
    # YYYY-MM-DD
    parts = text.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        y, m, d = parts
        if y.isdigit() and m.isdigit() and d.isdigit():
            return f"{y}{m.zfill(2)}{d.zfill(2)}"
    return text


@frappe.whitelist()
def get_pending_mwl(modality=None, limit=50):
    """
    Returns Labit Radiology Orders where mwl_pushed=0.
    The MWL worker polls this to know what to push to Orthanc.

    Returns a list of dicts with fields needed for a DICOM MWL dataset:
      name, patient, patient_name, patient_dob (YYYYMMDD), patient_sex (M/F/O),
      modality, study_description, scheduled_at (ISO), requisition.
    """
    try:
        filters = {"mwl_pushed": 0}
        if modality:
            filters["modality"] = modality

        orders = frappe.db.get_all(
            "Labit Radiology Order",
            filters=filters,
            fields=[
                "name",
                "patient",
                "patient_name",
                "patient_dob",
                "patient_sex",
                "modality",
                "study_description",
                "scheduled_at",
                "requisition",
            ],
            limit=int(limit),
            order_by="creation asc",
        )

        for order in orders:
            order["patient_dob"] = _dicom_date(order.get("patient_dob"))
            order["patient_sex"] = _normalize_sex(order.get("patient_sex"))

        return orders

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def mark_mwl_pushed(radiology_order_name, study_instance_uid, accession_uid=None):
    """
    Called by the MWL worker after successfully pushing a worklist entry to Orthanc.
    Sets mwl_pushed=1, mwl_pushed_at, study_instance_uid, and optionally accession_uid.
    Returns {status: "ok"} on success or {status: "error", message: ...} on failure.
    """
    try:
        doc = frappe.get_doc("Labit Radiology Order", radiology_order_name)
        doc.db_set("mwl_pushed", 1)
        doc.db_set("mwl_pushed_at", frappe.utils.now())
        doc.db_set("study_instance_uid", study_instance_uid)
        if accession_uid:
            doc.db_set("accession_uid", accession_uid)
        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def mark_images_received(radiology_order_name, image_count=None):
    """
    Called when images arrive in Orthanc (via Orthanc webhook or polling).
    Sets images_received=1, images_received_at, and image_count if provided.
    Returns {status: "ok"} on success or {status: "error", message: ...} on failure.
    """
    try:
        doc = frappe.get_doc("Labit Radiology Order", radiology_order_name)
        doc.db_set("images_received", 1)
        doc.db_set("images_received_at", frappe.utils.now())
        if image_count is not None:
            doc.db_set("image_count", int(image_count))
        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
