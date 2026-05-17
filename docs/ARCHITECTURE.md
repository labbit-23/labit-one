# Labit One — Architecture

## Overview

Labit One is a Frappe custom app (`labit_core`) that extends ERPNext. It provides the operational layer for diagnostic lab workflows: requisition through report delivery. ERPNext/Frappe/MariaDB is the authoritative enterprise backbone. Labit One never duplicates what ERPNext owns.

---

## Ownership Boundaries

### ERPNext / Frappe Owns

| Domain | Records |
|---|---|
| Identity | Patient master, Customer identity |
| Organisation | Company, Branch, Location |
| People | Employees, Users, Roles |
| Catalogue | Items (tests, packages), Item Groups, Pricelists |
| Finance | Sales Invoice, Payment Entry, Journal Entry, Accounting |
| Operations | Inventory, Stock, Purchase Orders |
| HR | Attendance, Leave, Payroll |

**Rule:** If it is an enterprise or organisational record, it lives in ERPNext/Frappe/MariaDB. Labit One references it by ID — it never copies or shadows it.

---

### Labit One Owns

| Domain | Ownership |
|---|---|
| Registration & Requisition | Diagnostic requisition workflow, requisition items |
| Sample Workflow | Sample creation, barcode/accession flow, collection events, receipt |
| Machine Integration | Analyzer connections, result ingestion, machine messages |
| Results & Validation | Result entry, validation rules, QC flags |
| Reports | Report generation, approval workflow, PDF delivery |
| Communication | WhatsApp bot, WABA sender, message log |
| Home Collection | Home visit scheduling, phlebotomist dispatch, logistics events |
| Intelligence | Patient trend reports, lab manager dashboards, CEO views |
| Platform Monitoring | Integration health UI, uptime dashboards, queue views |

---

### Labit CTO Engine (Supabase) Owns

| Domain | Records |
|---|---|
| Technical telemetry | Integration health events, HL7 parse errors |
| Uptime | Machine uptime records, connectivity checks |
| Queue diagnostics | Queue depth, failure rates, retry logs |

**Rule:** Supabase is not an operational database. No requisitions, no patients, no billing. Only platform monitoring data that has no business value in ERPNext.

---

## Data Ownership Rule

```
Operational data (lab workflow, patients, billing)  →  ERPNext / MariaDB
Platform monitoring (HL7 errors, uptime, queue health)  →  Labit CTO Engine (Supabase)
```

If in doubt: if a lab director would ask to see it, it belongs in ERPNext. If only the CTO would look at it, it belongs in Supabase.

---

## Core DocTypes

All DocTypes live in the `labit_core` Frappe custom app. Each must reference ERPNext masters where applicable and must never duplicate master data.

### `Labit Requisition`

The central unit of work. Every downstream record (sample, result, report) traces back to a Requisition ID.

| Field | Type | Links To |
|---|---|---|
| `patient` | Link | `Patient` (ERPNext) |
| `customer` | Link | `Customer` (ERPNext) |
| `company` | Link | `Company` (ERPNext) |
| `branch` | Link | `Branch` (ERPNext) |
| `requisition_date` | Datetime | — |
| `status` | Select | Registered / Sample Collected / Received / In Progress / Reported / Delivered |
| `sales_invoice` | Link | `Sales Invoice` (ERPNext) |
| `referred_by` | Link | `Employee` (ERPNext) — optional |
| `created_by` | Link | `User` (ERPNext) |
| `notes` | Text | — |

---

### `Labit Requisition Item`

Child table of `Labit Requisition`. One row per test/package ordered.

| Field | Type | Links To |
|---|---|---|
| `item` | Link | `Item` (ERPNext) |
| `item_name` | Data | (fetched from Item) |
| `qty` | Int | — |
| `rate` | Currency | — |
| `sample_type` | Data | — |
| `status` | Select | Pending / Collected / Received / Resulted |

---

### `Labit Sample`

Created when collection is confirmed. One sample per tube/container.

| Field | Type | Links To |
|---|---|---|
| `requisition` | Link | `Labit Requisition` |
| `patient` | Link | `Patient` (ERPNext) |
| `accession_number` | Data | — (generated, unique) |
| `barcode` | Barcode | — |
| `sample_type` | Data | — |
| `collected_by` | Link | `Employee` (ERPNext) |
| `collected_at` | Datetime | — |
| `status` | Select | Collected / In Transit / Received / Processing / Stored / Discarded |

---

### `Labit Sample Event`

Append-only audit log for every state change on a sample. Shape is fixed.

| Field | Type | Notes |
|---|---|---|
| `sample` | Link | `Labit Sample` |
| `requisition` | Link | `Labit Requisition` |
| `event_type` | Data | collected / received / rejected / transferred / etc. |
| `actor` | Link | `User` (ERPNext) |
| `actor_role` | Data | — |
| `timestamp` | Datetime | — |
| `payload` | JSON | event-specific detail |

**This table must be built before any machine integration or sample workflow is wired up.**

---

### `Labit Report Request`

Tracks report generation and delivery for a requisition.

| Field | Type | Links To |
|---|---|---|
| `requisition` | Link | `Labit Requisition` |
| `patient` | Link | `Patient` (ERPNext) |
| `status` | Select | Pending / Generating / Ready / Approved / Delivered |
| `report_file` | Attach | — |
| `approved_by` | Link | `User` (ERPNext) |
| `approved_at` | Datetime | — |
| `delivered_at` | Datetime | — |
| `delivery_channel` | Select | WhatsApp / Email / Portal / Print |

---

### `Labit Integration Event`

Audit log for all external system interactions (machines, HL7, APIs).

| Field | Type | Notes |
|---|---|---|
| `event_type` | Data | hl7_inbound / analyzer_result / api_call / etc. |
| `source` | Data | system or machine name |
| `requisition` | Link | `Labit Requisition` — optional |
| `status` | Select | Received / Parsed / Processed / Failed |
| `raw_payload` | Long Text | — |
| `error_message` | Text | — |
| `timestamp` | Datetime | — |

**Build this DocType before building any machine integration.**

---

### `Labit WhatsApp Message`

Decouples message triggering from the WhatsApp sender service.

| Field | Type | Links To |
|---|---|---|
| `patient` | Link | `Patient` (ERPNext) |
| `requisition` | Link | `Labit Requisition` — optional |
| `phone_number` | Data | — |
| `message_type` | Data | registration_confirm / report_ready / etc. |
| `status` | Select | Queued / Sent / Delivered / Failed |
| `sent_at` | Datetime | — |
| `waba_message_id` | Data | — |
| `payload` | JSON | — |

The WhatsApp sender service polls or listens for `Queued` records. Labit One operational code only writes to this table — it never calls WABA directly.

---

### `Labit Machine Message`

Raw inbound message from an analyzer or LIS machine, before parsing.

| Field | Type | Notes |
|---|---|---|
| `machine_id` | Data | — |
| `protocol` | Select | HL7 / ASTM / CSV / proprietary |
| `raw_message` | Long Text | — |
| `parsed` | Check | — |
| `integration_event` | Link | `Labit Integration Event` |
| `received_at` | Datetime | — |

---

## Design Principles

1. **ERPNext/Frappe is the source of truth for enterprise and organisational data.** If it exists in ERPNext, reference it — never copy it.

2. **Labit One extends ERPNext; it does not fight it.** All integration is through Frappe APIs and Python hooks. Never patch ERPNext core files.

3. **Use custom DocTypes and Frappe APIs, not ERPNext core modifications.** Custom fields on ERPNext DocTypes via `custom_fields` in fixtures are acceptable. Patching ERPNext Python files is not.

4. **Build workflow/action APIs for important operations, not only raw CRUD.** A requisition being "confirmed" is an action with side effects (sample creation, invoice trigger, notification queue). Expose it as a whitelisted API method, not a raw DocType save.

5. **Keep audit/event logging from day one.** Every state transition that matters to the lab must produce a `Labit Sample Event` or `Labit Integration Event` record before the feature ships.

6. **Keep machine integration and WhatsApp as services, not inside UI code.** Operational code writes records. Separate services consume them. These services can fail and retry independently.

7. **Build screens for speed where ERPNext UI is not operationally suitable.** Front desk registration, sample collection, and result entry require sub-second interactions. Standard Frappe forms are not fast enough for these workflows.

8. **Avoid two operational databases for the same workflow.** One requisition lives in one place: MariaDB via ERPNext/Frappe. There is no operational data in Supabase.

9. **Supabase is optional for CTO/telemetry only.** Labit One must function fully if Supabase is unavailable.

10. **First goal is working operational flow, not perfect architecture.** Phase 1 ships a working registration-to-sample-collection workflow at SDRC. Refactors happen in Phase 2.

11. **Every Labit DocType referencing an ERPNext record must validate that reference on save.** An orphaned requisition (pointing to a deleted patient) must raise a hard error, not silently save. Implement in `validate()` hooks.

12. **The Requisition is the core unit of work.** Every downstream record — sample, result, report, invoice, message — must carry a `requisition` link field. Orphaned records without a requisition link are a data integrity failure.

13. **Build the `Labit Integration Event` log before building any machine integration.** No analyzer connection, no HL7 parser, no result importer ships without its events being written to this log first.

---

## Phase 1 Target — Diagnostics Vertical Slice

```
Patient Search / Registration
        ↓
Labit Requisition (created, linked to ERPNext Patient)
        ↓
Requisition Items (tests/packages selected from ERPNext Item)
        ↓
Sample Collection Status (Labit Sample + Labit Sample Event)
        ↓
Billing Link (Sales Invoice created or linked in ERPNext)
```

---

## First Operational Screen — Requisition / Registration

**Performance target:** patient typeahead must resolve under 200ms.

**Capabilities:**
- Typeahead search by name, phone, DOB, MRN — queries ERPNext Patient via Frappe REST
- Inline new patient creation via ERPNext Patient API (no separate Labit patient table)
- Test/package selection from ERPNext Item list (filtered by Item Group)
- Requisition creation: writes `Labit Requisition` + `Labit Requisition Item` records
- Invoice: link existing Sales Invoice or trigger creation via ERPNext API
- Sample status: set to `Collected` on the requisition and create `Labit Sample` + `Labit Sample Event`
- Output: printable requisition reference with accession number(s)

---

## Frappe App

```bash
# Create the app
bench new-app labit_core

# Install on site
bench --site labit.local install-app labit_core
```

App lives at `apps/labit_core/` in this repo.
