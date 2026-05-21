# Deferred Features — Documented, Not Yet Built

These are confirmed requirements that are deliberately excluded from Phase 1.
Each entry has enough detail to build from without re-designing from scratch.

---

## Labit Referral Agreement

**What:** Per-doctor commercial arrangement for empanelled referring doctors.
**Why deferred:** Legal complexity (MCI/NMC ethics code), route varies by doctor and client.

**Design:**
- DocType: `Labit Referral Agreement` — one per empanelled doctor
- `agreement_type`: Consultant Fee / None (cash not recorded)
- `fee_basis`: Per Test / Per Requisition / Percentage of Bill
- `billing_entity`: Link → Supplier (doctor's clinic for payables)
- `applicable_tests`: child table — if empty, applies to all tests from this doctor
- `active_from / active_to`: agreement validity window
- At requisition save: if doctor is empanelled + Consultant Fee → create pending fee entry
- Month-end: generate ERPNext Supplier Invoice per doctor for all pending entries
- **Access:** Lab Manager and above only. Front desk sees empanelled flag only — never terms.
- **Out of scope permanently:** Cash arrangements. The system does not record what it should not know.

---

## Critical / Panic Value Alerting

**What:** When a result hits critical_low or critical_high threshold, immediately notify the referring doctor. NABL requirement.

**Design:**
- `Labit Critical Alert` DocType
- Triggered on result entry when flag = Critical Low or Critical High
- Fields: `sample`, `parameter`, `result_value`, `threshold`, `notified_via` (Call/WhatsApp/Email), `notified_at`, `acknowledged_by`, `acknowledged_at`
- No patient results can be approved until all critical alerts for that requisition are acknowledged
- WhatsApp notification to referring doctor via Labit Connect (Phase 2)

---

## Delta Check

**What:** Flag when a result has changed abnormally vs the same patient's previous result for the same parameter.

**Design:**
- `Labit Delta Check Rule` — per parameter: `max_absolute_change`, `max_percent_change`, `lookback_days`
- On result entry: fetch last result for this patient + parameter → compute delta → flag if exceeded
- Flagged results go to a Delta Check Review queue before approval

---

## Result Amendment

**What:** Post-release result correction with full audit trail. NABL requirement.

**Design:**
- Amendment creates a new `Labit Report Request` version linked to original
- Original report retained and marked superseded
- Amended report carries visible "AMENDED — replaces report dated DD/MM/YYYY" header
- `amended_reason`: mandatory free text
- `authorised_by`: Link → User (Lab Manager or above only)
- WhatsApp/email re-delivery triggered automatically

---

## Outsource / Reference Lab

**What:** Tests sent to an external reference lab. Billing: charge patient at own rate, pay reference lab at their rate.

**Design:**
- `Labit Outsource Order` — per sample or per test
- `reference_lab`: Link → Supplier
- `reference_lab_code`: their test code
- `expected_tat_hours`: Int
- `dispatched_at`, `result_received_at`
- `reference_lab_rate`: Currency (for payables)
- Result entered against original Requisition Item when received
- ERPNext Purchase Invoice raised to reference lab at their rate

---

## TAT Monitoring

**What:** Real-time turnaround time tracking with breach alerts.

**Design:**
- `tat_breach_at` computed on `Labit Sample` = `received_at` + `Labit Test.tat_hours`
- Scheduler job every 15 min: find samples past `tat_breach_at` still not resulted → alert Lab Manager
- TAT report: by test, by department, by date range, showing average and breach %

---

## Patient Consent

**What:** ABDM requires explicit patient consent before health records are shared. Some tests (HIV, genetic) require specific written consent.

**Design:**
- `Labit Patient Consent` child table on Patient
- `consent_type`: ABDM Data Sharing / HIV Test / Genetic Test / Marketing Communications
- `given_at`, `given_by` (staff), `revoked_at`
- ABDM consent has additional fields: `purpose`, `expiry`, `linked_hi_types` (per ABDM spec)

---

## Doctor Commission / Referral Report

**What:** Management-level MIS — revenue by referring doctor, test-wise.

**Design:**
- Report built from `Labit Requisition.referring_doctor` + `Labit Requisition Item`
- Not a DocType — a Frappe Report (Query Report or Script Report)
- Restricted to Lab Manager and above

---

## Appointment Scheduling

**What:** Three distinct scheduling flows that are operationally separate.

| Type | Description | Doctor-dependent |
|---|---|---|
| Home Collection | VE route + time slot at patient location | No |
| Imaging | Sonology, Echocardiography — slot per machine + doctor | Yes |
| Consultant | OPD doctor clinic schedule | Yes |

**Design:** Uses ERPNext `Patient Appointment` as the base.
- Home Collection: `Patient Appointment` + VE assignment + route grouping
- Imaging/Consultant: standard ERPNext scheduling with `Healthcare Practitioner Schedule`
- `Labit Requisition.appointment` links back to the `Patient Appointment` record

---

## Branch Routing Rules

**What:** When a lab has multiple branches, routing samples to the correct processing location automatically.

**Design:**
- `Labit Routing Rule` — `(branch, sample_type OR department) → Healthcare Service Unit`
- Applied during sample generation: if no `default_processing_unit` on `Labit Test Required Sample`, fall back to routing rule for the branch
- Manual override always permitted on individual `Labit Sample` records

---

## QC Module (Levey-Jennings, Westgard)

**What:** Machine control data, QC runs, calibration records, LJ plots, Westgard rule engine.

**Design:** Separate document — see planned `docs/decisions/qc-architecture.md`.
Key DocTypes: `Labit Instrument`, `Labit QC Material`, `Labit QC Target`, `Labit QC Run`, `Labit QC Result`, `Labit Calibration Event`.
Westgard rule violations block patient result approval for the affected instrument.

---

## ABHA API Integration

**What:** Verify ABHA numbers via ABDM API, push lab reports as FHIR R4 documents.

**Design:**
- `labit_core/api/abha.py` — whitelisted endpoint
- Verification flow: ABHA number → ABDM OTP → verify → mark `Labit Patient External ID.verified`
- Report push: FHIR R4 DiagnosticReport resource → ABDM HIE-CM
- Requires NHA registration as Health Information Provider (HIP)
- Sandbox: sandbox.abdm.gov.in

---

## Pharmacy (Future Hospital Clients)

**What:** Not relevant for pure diagnostic labs. Required if client is a polyclinic or hospital.
**Design:** Use ERPNext's native Pharmacy module. No Labit-specific DocTypes needed.

---

## Duplicate Patient Detection + Merge

**What:** Fuzzy match at registration when similar patients exist. Merge workflow for confirmed duplicates.

**Design:**
- On patient search: if new patient name + DOB is similar to existing → show warning with candidates
- `Labit Patient Merge Request` — supervisor approves, system merges requisition history to surviving MRN

---

## Parameter Groups + Report Schema (Phase 2 — Reporting Layer)

**What:** Grouping of parameters for structured report output, and the ability to define multiple report layouts per test.

**Why deferred:** Machine integration (instrument test map + result ingestion) operates at the parameter level and does not require report schema. Schema is needed before PDF report generation is built.

**Design:**

### Labit Parameter Group
A reusable named grouping of parameters displayed as a block on the report.

- `group_name`: Data (e.g. "Electrolytes", "Differential Count", "Proteins")
- `validation_rule`: Select — None / Sum to 100 (for differential counts — blocks approval if parameters in group don't sum to 100)
- `parameters`: child table — ordered list of `Labit Test Parameter` links (display_order is row sequence)

### Labit Report Schema
Defines the layout for one variant of a test's report. A test can have multiple schemas.

- `test`: Link → Labit Test
- `schema_name`: Data (e.g. "Rapid", "Quantitative", "Positive Samples")
- `is_default`: Check — the schema used unless overridden at result entry
- `has_overall_impression`: Check — adds a free-text "Overall Impression / Interpretation" field at the end (e.g. HIV Positive Samples)
- `items`: child table — ordered mixed list, each row is **either**:
  - `parameter`: Link → Labit Test Parameter (directly placed parameter)
  - `parameter_group`: Link → Labit Parameter Group (block of grouped parameters)
  - (one or the other per row, not both; validation enforces this)

**Key invariant:** `Labit Test Parameter` itself carries no grouping or display-order information. Grouping and ordering live entirely in the schema. The same parameter can appear in multiple schemas in different positions or groups.

**HIV example:**
- Test: HIV Antibody
  - Schema "Rapid" (default): items = [parameter: Reactivity]
  - Schema "Quantitative": items = [parameter: CD4 Count, parameter: Viral Load]
  - Schema "Positive Samples": items = [parameter: Reactivity, parameter: Viral Load, parameter: CD4 Count], has_overall_impression = true

**Differential Count rule:** Create a `Labit Parameter Group` "Differential Count" with validation_rule = "Sum to 100". At result approval, if any parameter in this group is unresulted or the group doesn't sum to 100, approval is blocked with a clear error.
