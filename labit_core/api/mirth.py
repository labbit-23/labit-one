import frappe
from frappe import _


VALID_SAMPLE_STATUSES = [
    "Unissued", "Issued", "Collected", "In Transit",
    "Received", "Processing", "Stored", "Discarded", "Rejected",
]


# ---------------------------------------------------------------------------
# save_results  — primary inbound endpoint, replaces Shivam saveResultsAPI
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def save_results(
    sample_no,
    device_id,
    organization_id=None,
    patient_id=None,
    raw_data=None,
    results=None,
):
    """
    Batch result POST from Mirth after analyzer produces HL7 ORU output.

    Mirth payload (JSON body, keys normalised to snake_case here):
        SampleNo        → sample_no       (Labit Sample name, e.g. SM-2026-00001)
        DeviceId        → device_id       (MSH.3.1, e.g. "MindrayBS240")
        OrganizationId  → organization_id (ignored for now, for audit only)
        PatientId       → patient_id      (for audit log only)
        RawData         → raw_data        (full raw HL7 blob)
        Results         → results         (list of {TestName, Value, Units, Timestamp})

    Resolution chain per result item:
        1. Look up Labit Sample by sample_no → get sample_type + time_point_minutes
        2. Look up Labit Instrument Test Map:
               instrument_id = device_id
               machine_test_name = result["TestName"]
               sample_type = sample.sample_type  (falls back to null-wildcard if no exact match)
               time_point_minutes = sample.time_point_minutes (default 0)
        3. Create / update Labit Result for each matched parameter.

    Never throws — returns {status, saved, skipped, errors} so Mirth doesn't crash.
    """
    import json

    if isinstance(results, str):
        try:
            results = json.loads(results)
        except Exception:
            return {"status": "error", "message": "results is not valid JSON"}

    if not results:
        return {"status": "error", "message": "results list is empty"}

    # 1. Audit log — created unconditionally so every message is traceable.
    msg_doc = _create_machine_message(
        raw_message=raw_data,
        instrument_id=device_id,
        message_type="HL7 ORU",
    )

    # 2. Resolve sample.
    sample = _resolve_sample(sample_no)
    if sample is None:
        _mark_message_error(msg_doc, "Sample not found: {0}".format(sample_no))
        return {"status": "error", "message": "Sample not found: {0}".format(sample_no)}

    requisition_name = sample.requisition

    saved, skipped, errors = [], [], []

    for item in results:
        test_name = (item.get("TestName") or "").strip()
        raw_value = (item.get("Value") or "").strip()
        units = (item.get("Units") or "").strip() or None
        result_flag = (item.get("Flag") or "").strip() or None

        if not test_name or not raw_value:
            skipped.append({"test_name": test_name, "reason": "empty name or value"})
            continue

        # 3. Resolve parameter via instrument map.
        parameter_name, test_name_resolved, resolution_note = _resolve_parameter(
            device_id, test_name, sample.sample_type, sample.time_point_minutes or 0
        )
        if not parameter_name:
            skipped.append({"test_name": test_name, "reason": resolution_note})
            continue

        # 4. Upsert Labit Result.
        try:
            result_name = _upsert_result(
                requisition=requisition_name,
                sample=sample_no,
                test=test_name_resolved,
                parameter=parameter_name,
                raw_value=raw_value,
                units=units,
                result_flag=result_flag,
                instrument_id=device_id,
                msg_ref=msg_doc.name,
            )
            saved.append({"test_name": test_name, "result": result_name})
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "mirth.save_results upsert error")
            errors.append({"test_name": test_name, "error": str(e)})

    # 5. Mark message processed if at least one result landed.
    if saved:
        try:
            msg_doc.processed = 1
            msg_doc.processed_at = frappe.utils.now()
            msg_doc.linked_requisition = requisition_name
            msg_doc.linked_sample = sample_no
            if saved:
                msg_doc.linked_result = saved[-1]["result"]
            msg_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "mirth.save_results message update")
    else:
        frappe.db.commit()

    status = "ok" if not errors else ("partial" if saved else "error")
    return {
        "status": status,
        "saved": saved,
        "skipped": skipped,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# check_duplicate  — replaces Shivam checkDuplicateAPI
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def check_duplicate(sample_no, test_name, device_id=None):
    """
    Returns {"exists": true/false, "result": result_name_or_null}.
    Mirth calls this before save_results to skip already-posted results.

    sample_no:  Labit Sample name
    test_name:  machine test name (as sent by the analyzer)
    device_id:  instrument ID (needed to resolve parameter via instrument map)
    """
    sample = _resolve_sample(sample_no)
    if sample is None:
        return {"exists": False, "result": None}

    parameter_name, _, _ = _resolve_parameter(
        device_id or "", test_name, sample.sample_type, sample.time_point_minutes or 0
    )
    if not parameter_name:
        return {"exists": False, "result": None}

    existing = frappe.db.get_value(
        "Labit Result",
        {"sample": sample_no, "parameter": parameter_name},
        "name",
    )
    return {"exists": bool(existing), "result": existing}


# ---------------------------------------------------------------------------
# check_orders  — replaces Shivam checkOrdersAPI
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def check_orders(sample_no):
    """
    Returns {"order_count": N} — N > 0 means this sample has ordered tests in labit-one.
    Mirth calls this to confirm the sample is expected before posting results.
    """
    if not frappe.db.exists("Labit Sample", sample_no):
        return {"order_count": 0}

    requisition = frappe.db.get_value("Labit Sample", sample_no, "requisition")
    if not requisition:
        return {"order_count": 0}

    count = frappe.db.count("Labit Requisition Item", {"parent": requisition})
    return {"order_count": count}


# ---------------------------------------------------------------------------
# check_sample_details  — replaces Shivam checkSampleDetailsAPI
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def check_sample_details(sample_no):
    """
    Returns patient demographics for the sample — used by Mirth for logging/LIS audit.
    Returns {"found": false} if sample doesn't exist.
    """
    sample = frappe.db.get_value(
        "Labit Sample",
        sample_no,
        ["requisition", "sample_type", "sample_type_name", "time_point_minutes", "time_label"],
        as_dict=True,
    )
    if not sample:
        return {"found": False}

    req = frappe.db.get_value(
        "Labit Requisition",
        sample.requisition,
        ["patient_name", "patient_dob", "patient_sex", "status"],
        as_dict=True,
    ) if sample.requisition else {}

    return {
        "found": True,
        "sample_no": sample_no,
        "requisition": sample.requisition,
        "sample_type": sample.sample_type_name or sample.sample_type,
        "time_point_minutes": sample.time_point_minutes or 0,
        "time_label": sample.time_label or "",
        "patient_name": req.get("patient_name") if req else None,
        "patient_dob": str(req.get("patient_dob") or "") if req else None,
        "patient_sex": req.get("patient_sex") if req else None,
        "requisition_status": req.get("status") if req else None,
    }


# ---------------------------------------------------------------------------
# get_pending_requisitions  — Mirth polls to know what samples are in lab
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def get_pending_requisitions(limit=50):
    """
    Returns requisitions ready for processing.
    Mirth polls this to know what samples are in the lab.
    """
    requisitions = frappe.db.sql("""
        SELECT
            r.name,
            r.patient_name,
            r.patient_dob,
            r.patient_sex,
            r.requisition_date,
            r.status
        FROM `tabLabit Requisition` r
        WHERE r.status IN ('Sample Collected', 'Received', 'In Progress')
        ORDER BY r.requisition_date ASC
        LIMIT %(limit)s
    """, {"limit": int(limit)}, as_dict=True)

    result = []
    for req in requisitions:
        items = frappe.db.sql("""
            SELECT
                ri.test AS test_code,
                ri.sample_type_name,
                COUNT(tp.name) AS parameter_count
            FROM `tabLabit Requisition Item` ri
            LEFT JOIN `tabLabit Test Parameter Link` tpl ON tpl.parent = ri.test
            LEFT JOIN `tabLabit Test Parameter` tp ON tp.name = tpl.parameter
            WHERE ri.parent = %(req)s
            GROUP BY ri.test, ri.sample_type_name
        """, {"req": req.name}, as_dict=True)

        result.append({
            "name": req.name,
            "patient_name": req.patient_name,
            "patient_dob": str(req.patient_dob) if req.patient_dob else None,
            "patient_sex": req.patient_sex,
            "requisition_date": str(req.requisition_date) if req.requisition_date else None,
            "items": items,
        })

    return result


# ---------------------------------------------------------------------------
# update_sample_status  — Mirth signals sample acknowledgement by analyzer
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=False)
def update_sample_status(sample_no, new_status, instrument_id=None):
    """
    Updates Labit Sample status when analyzer acknowledges a sample.
    Returns {status: "ok"} or {status: "error", message: ...}. Never throws.
    """
    try:
        if new_status not in VALID_SAMPLE_STATUSES:
            return {
                "status": "error",
                "message": "Invalid status '{0}'. Valid: {1}".format(
                    new_status, ", ".join(VALID_SAMPLE_STATUSES)
                ),
            }

        if not frappe.db.exists("Labit Sample", sample_no):
            return {"status": "error", "message": "Sample not found: {0}".format(sample_no)}

        sample_doc = frappe.get_doc("Labit Sample", sample_no)
        sample_doc.status = new_status
        sample_doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "ok"}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "mirth.update_sample_status error")
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_sample(sample_no):
    """Return a dict with requisition, sample_type, time_point_minutes, or None."""
    return frappe.db.get_value(
        "Labit Sample",
        sample_no,
        ["requisition", "sample_type", "time_point_minutes"],
        as_dict=True,
    )


def _resolve_parameter(instrument_id, machine_test_name, sample_type, time_point_minutes):
    """
    Look up Labit Instrument Test Map with fallback logic:
      1. Exact match: instrument_id + machine_test_name + sample_type + time_point_minutes
      2. Wildcard sample_type (null): instrument_id + machine_test_name + time_point_minutes
      3. If still not found, return (None, None, reason_string).

    Returns (parameter_name, labit_test_name, note).
    """
    time_point = int(time_point_minutes or 0)

    def _query(with_sample_type):
        filters = {
            "instrument_id": instrument_id,
            "machine_test_name": machine_test_name,
            "time_point_minutes": time_point,
        }
        if with_sample_type:
            filters["sample_type"] = sample_type
        else:
            filters["sample_type"] = ["is", "not set"]
        return frappe.db.get_value(
            "Labit Instrument Test Map",
            filters,
            ["labit_parameter", "labit_test"],
            as_dict=True,
        )

    # Exact match first.
    if sample_type:
        row = _query(with_sample_type=True)
        if row:
            return row.labit_parameter, row.labit_test, "exact match"

    # Wildcard fallback (sample_type not set in map).
    row = _query(with_sample_type=False)
    if row:
        return row.labit_parameter, row.labit_test, "wildcard sample_type match"

    return (
        None,
        None,
        "no mapping for instrument={0} test='{1}' sample_type={2} time_point={3}".format(
            instrument_id, machine_test_name, sample_type, time_point
        ),
    )


def _upsert_result(
    requisition, sample, test, parameter,
    raw_value, units, result_flag, instrument_id, msg_ref
):
    """Create or update a Labit Result. Returns the result document name."""
    is_numeric = False
    numeric_value = None
    try:
        numeric_value = float(raw_value)
        is_numeric = True
    except (TypeError, ValueError):
        pass

    existing_name = frappe.db.get_value(
        "Labit Result",
        {"sample": sample, "parameter": parameter, "requisition": requisition},
        "name",
    )

    if existing_name:
        doc = frappe.get_doc("Labit Result", existing_name)
    else:
        doc = frappe.new_doc("Labit Result")
        doc.requisition = requisition
        doc.sample = sample
        doc.test = test
        doc.parameter = parameter

    doc.is_machine_generated = 1
    doc.status = "Entered"
    doc.instrument_id = instrument_id
    doc.raw_message_ref = msg_ref

    if units:
        doc.result_unit = units
    if result_flag:
        doc.result_flag = result_flag

    if is_numeric:
        doc.result_type = "Numeric"
        doc.result_numeric = numeric_value
    else:
        doc.result_type = "Text"
        doc.result_text = str(raw_value)

    if existing_name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    return doc.name


def _create_machine_message(raw_message, instrument_id, message_type):
    """Insert a Labit Machine Message audit record and return the doc."""
    doc = frappe.get_doc({
        "doctype": "Labit Machine Message",
        "received_at": frappe.utils.now(),
        "message_type": message_type,
        "source_instrument": instrument_id,
        "raw_message": raw_message,
        "processed": 0,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def _mark_message_error(msg_doc, error_text):
    """Update the machine message audit record with an error, silently."""
    try:
        msg_doc.error_message = error_text[:140]
        msg_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass
