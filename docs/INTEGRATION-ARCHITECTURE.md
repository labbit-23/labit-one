# Labbit × ERPNext — Migration Architecture Document
*May 2026 — Draft for review*

---

## 1. Executive Summary

Shivam-Neosoft (the current LIS + reporting stack) is being replaced by ERPNext with a custom Frappe app (`labbit_lims`). Labbit (Next.js) stays as the field operations and patient engagement layer. Mirth Connect stays as the integration middleware but is repointed from Shivam → ERPNext APIs. Orthanc stays as the DICOM/MWL server.

**What changes:** The backend data store and workflow engine (Shivam → ERPNext + labbit_lims). What Neosoft delivered (report rendering, dispatch) moves into Labbit's existing dispatch layer.

**What stays:** Mirth (config change only), Orthanc (feed source changes), Labbit (new API targets, new screens added), Python ASTM converters (activated for first time).

**Goal:** A fully integrated, owned stack. No third-party LIS vendor lock-in. ERPNext handles billing, patient master, clinical workflow. Labbit handles field operations, patient engagement, and frontend for all non-finance workflows.

---

## 2. Current State

```
Walk-in / Phone
    │
    ▼
Shivam (LIS)
  ├── Patient registration
  ├── Requisition / TRF creation
  ├── Accession number issuance
  ├── Test catalog
  ├── Result entry / approval
  └── Billing (partial)
    │
    ├── Mirth Connect (REST API ↔ Shivam)
    │     └── Analyzer machines → Mirth → POST results to Shivam
    │         (Python ASTM→HL7 converters exist but NOT activated)
    │
    ├── Orthanc (DICOM server + MWL)
    │     └── Fed from Shivam for imaging worklist
    │
    └── Neosoft (sits on top of Shivam)
          ├── Report formatting and PDF generation
          ├── Patient-facing report delivery
          └── Labbit fetches via Neosoft API (report lookup, PDF URL, trends)

Labbit (Next.js)  ←── separate system, home visits only
  ├── Visit scheduling + phlebo dispatch
  ├── Patient portal (fetches from Neosoft API)
  ├── WhatsApp bot (report delivery via Neosoft)
  └── QuickBook → admin converts → Visit
```

---

## 3. Target State

```
Walk-in / Home Visit Request
    │
    ▼
Labbit UI (Next.js)  ←── patient-facing and field ops frontend
  ├── Visit / Lab Request created
  ├── Itemized test list: patient adds/removes/changes
  ├── Total shown → patient confirms
  │
  ▼ (on payment)
ERPNext + labbit_lims  ←── replaces Shivam-Neosoft
  ├── Patient master (source of truth)
  ├── Test catalog (Lab Test Template doctype)
  ├── Requisition / Lab Accession (custom doctype)
  │     ├── Accession number issued (series: ACC-YYYY-NNNN)
  │     └── TRF generated (Labbit fetches structured data, renders PDF)
  ├── Billing: Sales Invoice auto-created from Lab Test (ERPNext native)
  ├── Result entry (Labbit custom UI → ERPNext API)
  ├── Pathologist approval (Frappe workflow engine)
  ├── Radiology order + report (custom doctype, linked to Orthanc study UID)
  └── Webhook on result approval → Labbit dispatch
    │
    ├── Mirth Connect  ←── ALWAYS in middle, config repoint only
    │     ├── Input: Analyzer machine output
    │     │     └── Python ASTM→HL7 converters → Mirth HL7 channel (ACTIVATE)
    │     └── Output: REST API → labbit_lims endpoints (was: Shivam endpoints)
    │
    ├── Orthanc (unchanged)
    │     ├── DICOM server (PACS)
    │     ├── MWL server → fed from ERPNext labbit_lims instead of Shivam
    │     └── Study UID linked back to ERPNext Radiology order
    │
    └── Labbit (dispatch layer, unchanged role)
          ├── Receives webhook from ERPNext on result approval
          ├── Dispatches: WhatsApp, SMS, patient portal
          ├── Bot: patient requests report → Labbit fetches from ERPNext API
          └── Patient portal: fetches results from ERPNext instead of Neosoft
```

---

## 4. System Responsibilities (Clear Ownership)

| Domain | Owner | Notes |
|--------|-------|-------|
| Patient master | ERPNext | Single source of truth. Labbit syncs via `patient_external_keys` |
| Test catalog (tests, packages, normal ranges, units) | ERPNext Lab Test Template | Labbit fetches for UI |
| Accession number issuance | labbit_lims (custom Frappe app) | Series: ACC-YYYYMMDD-NNNN |
| TRF generation | Labbit renders | Fetches structured data from ERPNext, generates PDF |
| Billing / invoicing | ERPNext native | Sales Invoice auto-linked to Lab Test. Finance team uses ERPNext UI |
| Result entry UI | Labbit Next.js | Calls ERPNext API. Staff never see ERPNext's form UI |
| Result approval / sign-off | ERPNext Frappe workflow | Pathologist uses custom Labbit UI or ERPNext (internal, acceptable) |
| Radiology order (MWL) | labbit_lims | Creates Orthanc MWL entry, links back study UID |
| DICOM storage + viewer | Orthanc | Unchanged |
| Instrument communication | Mirth + Python converters | ASTM → HL7 → Mirth → labbit_lims REST |
| Home visit scheduling | Labbit | Unchanged |
| Phlebo field ops | Labbit | Unchanged |
| Patient portal | Labbit | Fetches from ERPNext instead of Neosoft |
| WhatsApp bot | Labbit | Unchanged flow, new data source |
| Report dispatch | Labbit | Triggered by ERPNext webhook on approval |
| Campaign / re-engagement | Labbit | Unchanged |
| System monitoring (CTO) | Labbit | ERPNext service added to health dashboard |

---

## 5. labbit_lims — Custom Frappe App Specification

This is the core of the migration. `labbit_lims` is a Frappe app installed inside ERPNext that adds what ERPNext Healthcare doesn't have out of the box.

### 5.1 New Doctypes

#### Lab Accession
The sample-as-hero entity. One accession = one sample = one or many tests.

| Field | Type | Notes |
|-------|------|-------|
| accession_number | Data | Auto-series ACC-YYYYMMDD-NNNN, unique |
| patient | Link → Patient | ERPNext Patient |
| visit_id | Data | Labbit visit ID (nullable — home visits only) |
| lab_tests | Table | Child table: linked Lab Test records |
| status | Select | pending, sample_collected, processing, resulted, approved, dispatched |
| sample_collected_at | Datetime | |
| sample_collected_by | Link → Healthcare Practitioner | |
| notes | Text | |
| trf_generated_at | Datetime | When Labbit pulled TRF data |

#### Radiology Order
Imaging-as-patient-hero entity. Linked to Orthanc study.

| Field | Type | Notes |
|-------|------|-------|
| patient | Link → Patient | |
| study_instance_uid | Data | DICOM Study UID from Orthanc |
| accession_number | Data | Links to Lab Accession if combined visit |
| modality | Select | CT, MRI, X-Ray, Ultrasound, etc. |
| mwl_pushed_at | Datetime | When MWL entry was created in Orthanc |
| radiologist | Link → Healthcare Practitioner | |
| report_status | Select | pending, dictated, uploaded, approved |
| report_text | Long Text | Radiologist narrative |
| report_approved_at | Datetime | |

#### Webhook Registration
For Labbit to register its dispatch endpoint.

| Field | Type | Notes |
|-------|------|-------|
| url | Data | Labbit webhook receiver endpoint |
| events | Table | result_approved, accession_created, payment_done, etc. |
| secret | Password | HMAC signing secret |
| active | Check | |

### 5.2 API Surface (Mirth-compatible)

Mirth currently calls these operations on Shivam. `labbit_lims` must expose equivalent endpoints:

| Operation | Current (Shivam) | New (labbit_lims) |
|-----------|-----------------|-------------------|
| Get pending requisitions | GET /shivam/requisitions?status=pending | GET /api/method/labbit_lims.api.get_pending_accessions |
| Post result for a test | POST /shivam/results | POST /api/method/labbit_lims.api.post_result |
| Update accession status | PUT /shivam/requisition/{id}/status | PUT /api/method/labbit_lims.api.update_accession_status |
| Get patient by phone/MRN | GET /shivam/patient?phone={} | GET /api/method/labbit_lims.api.get_patient |
| Get test catalog | GET /shivam/tests | GET /api/resource/Lab Test Template |
| Push MWL entry | POST /shivam/mwl | POST /api/method/labbit_lims.api.push_mwl (→ Orthanc) |

> **Note:** The exact Shivam API contract needs to be captured from Mirth channel configs before `labbit_lims` APIs are finalised. Mirth channel export is the source of truth for what Shivam currently receives/returns.

### 5.3 Webhook Dispatcher
On these events in ERPNext, fire registered webhooks to Labbit:
- `Lab Accession` → status changes to `approved`
- `Radiology Order` → status changes to `approved`
- `Sales Invoice` → submitted (payment confirmed)
- `Lab Accession` → created (for Labbit to update visit status)

Frappe has a native Webhook doctype — use it. No custom dispatcher needed.

---

## 6. Labbit Changes Required

### 6.1 New API routes in Labbit (Next.js)

| Route | Purpose |
|-------|---------|
| `POST /api/erpnext/webhook` | Receive ERPNext webhooks (result approved → dispatch) |
| `GET /api/erpnext/patient?phone=` | Proxy patient lookup to ERPNext |
| `POST /api/erpnext/accession` | Create Lab Accession in ERPNext from visit |
| `GET /api/erpnext/tests` | Fetch test catalog from ERPNext for UI |
| `GET /api/erpnext/result/{accession}` | Fetch results for patient portal |
| `GET /api/erpnext/trf/{accession}` | Fetch structured TRF data for PDF render |

All routes proxy to ERPNext using API key + secret (stored in Labbit env, never exposed to browser).

### 6.2 New Labbit UI screens

| Screen | Route | Purpose |
|--------|-------|---------|
| Lab Visit / Quote | `/lab-visit` or modal | Patient selects tests, sees total, confirms |
| TRF view | `/trf/{accession}` | Printable TRF form |
| Result entry | `/admin/results` | Lab staff enter results — calls ERPNext API |
| Accession list | `/admin/accessions` | Replaces the Neosoft report list in admin |

### 6.3 Existing Labbit changes

| Component | Change |
|-----------|--------|
| Patient portal (`/patient`) | Fetch results from ERPNext API instead of Neosoft API |
| WhatsApp bot report handler | Fetch from ERPNext instead of Neosoft |
| Report dispatch | Triggered by ERPNext webhook instead of polling Neosoft |
| `patient_external_keys` | Add `erpnext_patient_id` as an external key type |
| Visit creation | On visit accepted → create Lab Accession in ERPNext |

### 6.4 API key auth (currently missing — must build)
ERPNext needs to call Labbit's webhook endpoint securely. Add:
- `api_keys` table in Supabase (key, secret_hash, name, active, permissions)
- Middleware in Labbit API routes that validates `X-API-Key` header
- HMAC signature verification on webhook receiver

---

## 7. Mirth Migration

**Principle: config change only. No Mirth logic rebuild.**

### Steps
1. Export all current Mirth channel configs (as XML backup before touching anything)
2. For each channel that POSTs/GETs/PUTs to a Shivam URL:
   - Replace base URL: `https://shivam.*/` → `https://erpnext.*/`
   - Update endpoint paths to match `labbit_lims` API surface (Section 5.2)
   - Update auth headers: Shivam credentials → ERPNext API key + secret
3. Activate Python ASTM→HL7 converter channels:
   - Configure as Mirth source connector (File/TCP listener)
   - Output as HL7 ORU message
   - Route to `labbit_lims` result POST endpoint
4. Test each channel against ERPNext staging before cutover

### What to capture from Mirth before starting
- Full channel list with source/destination types
- For each channel: the exact Shivam endpoint called, HTTP method, payload structure, response handling
- This becomes the `labbit_lims` API spec (fills in the gaps in Section 5.2)

---

## 8. Orthanc Integration

**Unchanged infrastructure. Feed source changes.**

| Currently | After migration |
|-----------|----------------|
| Shivam pushes MWL entries to Orthanc | `labbit_lims` `push_mwl` API calls Orthanc |
| Orthanc Study UID not tracked in Shivam | Orthanc Study UID stored in `Radiology Order` doctype |
| DICOM images stored in Orthanc | Unchanged |

When an imaging test is in a requisition:
1. ERPNext creates a `Radiology Order` record
2. `labbit_lims.api.push_mwl` is called → creates C-FIND MWL entry in Orthanc
3. Machine queries Orthanc MWL, gets patient + study details, starts acquisition
4. DICOM images pushed back to Orthanc
5. Radiologist opens Orthanc viewer, reads, dictates into ERPNext Radiology Order
6. Approval → webhook → Labbit dispatch

---

## 9. Data Model Alignment

### Patient identity across systems

| System | Patient ID field |
|--------|-----------------|
| Labbit | `patients.id` (UUID) |
| ERPNext | `Patient.name` (docname, e.g. PAT-00001) |
| Orthanc | DICOM Patient ID (maps to ERPNext Patient name) |
| Shivam (legacy) | Shivam patient ID |

Sync via `patient_external_keys` table (already exists in Labbit):
```
patient_id (Labbit UUID) → external_key (ERPNext PAT-XXXXX), lab_id, key_type='erpnext_patient'
```

On visit creation: Labbit looks up ERPNext patient by phone → if not found, creates → stores ERPNext ID in `patient_external_keys`.

### Accession ↔ Visit linkage

```
Labbit visits.id  ←──  Lab Accession.visit_id (nullable)
                        (home visits only; walk-in accessions have no visit_id)
```

---

## 10. Migration Steps (Ordered)

| Step | Work | Dependency | Risk |
|------|------|-----------|------|
| 1 | Export Mirth channel configs. Document exact Shivam API contract. | None — do first | Low |
| 2 | Set up ERPNext instance. Install Healthcare module. Create `labbit_lims` app scaffold. | Step 1 | Low |
| 3 | Build core `labbit_lims` doctypes: Lab Accession, Radiology Order | Step 2 | Medium |
| 4 | Build `labbit_lims` API surface matching Shivam contract from Step 1 | Steps 1, 3 | Medium |
| 5 | Build Labbit ↔ ERPNext bridge: patient sync, accession creation, result fetch | Step 4 | Medium |
| 6 | Build Labbit result entry UI + accession list (replacing Neosoft UI) | Step 5 | Medium |
| 7 | Activate Python ASTM→HL7 converters in Mirth staging, test against ERPNext staging | Steps 4, 3 | Medium |
| 8 | Migrate test catalog from Shivam → ERPNext Lab Test Templates | Step 2 | Low |
| 9 | Historical data import: run Shivam → ERPNext background sync (patients, requisitions, results, PDFs) | Step 2 | High |
| 10 | Repoint Mirth channels: Shivam → ERPNext staging. Full regression test. | Steps 4, 7 | High |
| 11 | Repoint Orthanc MWL feed → ERPNext labbit_lims | Step 4 | Medium |
| 12 | Switch Labbit patient portal + bot: Neosoft API → ERPNext API | Step 5 | Low |
| 13 | Production cutover (Mirth + Orthanc repoint to prod ERPNext) | All above | High |
| 14 | Decommission Shivam-Neosoft (after import verified complete) | Step 9, 13 | Low |

**Step 9 — Historical data import (not a Mirth dual-write):**
Mirth is repointed once, cleanly, at cutover. There is no period where Mirth writes to both systems.

The "30-day window" is the period a background Python sync service runs, pulling Shivam historical data into ERPNext before Shivam is switched off. New live work goes directly to labit-one from cutover day. Historical data arrives in the background.

**Scope:** Shivam holds data going back to ~2013-14. Priority order for import:
1. Last 2-3 years first — most relevant for pathologist approval context and patient trend views
2. Older records in subsequent batches, working backwards

**Data imported per patient:**
- ERPNext `Patient` record (dedup by phone + name + DOB before creating)
- `Labit Patient External ID` (id_type: Shivam, for cross-reference)
- Historical `Labit Requisition` records — **full history from ~2013** (source = Shivam Import, is_archived = 1, shivam_id stored for dedup)
- Historical `Labit Result` records at parameter level — **full history from ~2013** (is_archived = 1)
- iReport PDFs — **last 2 years only**, fetched from Neosoft API and attached to the corresponding report record in ERPNext. Older records carry the structured result data only; the UI shows "Historical record — report PDF not available for this period."

**Why PDFs only 2 years:** Attaching 10+ years of PDFs would overload ERPNext file storage and is not clinically necessary — structured result data is sufficient for trend views and delta checks. The 2-year PDF window covers the period most relevant to active patient care.

**Import service design:**
- Python script in `labbit-py` or `py_utils`
- Reads from **custom Shivam APIs** (Tomcat/Java) written specifically for this import — no Oracle driver, no `cx_Oracle`. The Shivam team writes whatever extraction endpoints the import needs (patients, requisitions, parameter-level results, PDF links).
- Writes to ERPNext via Frappe REST client or direct bench call
- Idempotent: checks `shivam_id` / `external_id` before inserting — safe to re-run
- `Labit Import Batch` doctype tracks each run: timestamp, records synced, errors, resume offset
- `source` field (Native / Shivam Import) + `is_archived = 1` on historical Requisition, Result, and Report records

**PDF handling:**
- PDF pull reuses/extends existing `labbit-py` worker logic (workers already pull PDFs from Neosoft)
- PDFs stored **without the lab header** (logo, address, NABL block) — stripped at pull time to keep files lean
- When ERPNext serves a historical report it applies its own header template over the stored content
- 2-year window only — older records: structured result data present, no PDF attached, UI shows "Report PDF not available for records before [date]"

**Decommission gate:** Shivam is not decommissioned until the import batch log shows zero errors and the last-2-years data set is fully verified in ERPNext. Older records can continue importing after cutover if needed.

---

## 11. Frontend Strategy

**Rule: ERPNext's UI is never shown to patients or field workers. It is shown only to finance/billing staff (acceptable) and optionally to pathologists for approval (can be replaced with Labbit UI if needed).**

| User | Frontend |
|------|----------|
| Patient (portal, TRF, reports) | Labbit Next.js |
| Phlebo (field ops) | Labbit Next.js |
| Logistics | Labbit Next.js |
| Admin (visits, accessions, result entry) | Labbit Next.js calling ERPNext API |
| Lab staff (result entry) | Labbit Next.js custom result entry UI |
| Pathologist (approval) | Labbit Next.js OR ERPNext (internal, acceptable) |
| Finance / billing | ERPNext native (acceptable — finance team, desktop) |
| Director / CTO | Labbit CTO dashboard (add ERPNext service health to it) |

---

## 12. Open Questions (Needed Before Development Starts)

| # | Question | Status | Why it matters |
|---|----------|--------|---------------|
| Q1 | Mirth channel list and Shivam API contract | ✅ Resolved — Mirth XMLs at `/Users/pav/projects/MIRTH/`. 6 machine channels (HL7 MLLP), 3 Orthanc channels, Tricog ECG. API surface documented in `labit_core/api/mirth.py`. | Was blocking `labbit_lims` API design |
| Q2 | How many test templates are in Shivam? | ❓ Open | Sizes the Step 8 catalog migration and the `Labit Instrument Test Map` seeding effort |
| Q3 | How many patients + requisitions are in Shivam? (going back to ~2013-14) | ❓ Open | Determines import batch sizing, Oracle query strategy, and whether Neosoft PDF API can serve all historical PDFs or direct Oracle + file server access is needed |
| Q4 | Which machines are ASTM (Sysmex, D10, Neolyte) — are their Mirth channels production-ready or DEV-only? | ❓ Open — DEV folder suggests not yet in production | Determines scope of Step 7 |
| Q5 | Is billing currently in Shivam or a separate system? | ❓ Open | Determines if historical invoice records need to migrate or are already in a separate accounting system |
| Q6 | Pathologist approval UI — Labbit Next.js custom UI or ERPNext native form acceptable? | ❓ Open | Scope of Labbit frontend build |
| Q7 | Multi-branch: how many locations, shared or separate Orthanc instance? | ❓ Open | ERPNext multi-branch vs multi-company setup; Orthanc routing |
| Q8 | What data does the Shivam import API need to expose? (patients, requisitions, parameter-level results, PDF links) | ✅ Approach resolved — custom APIs will be written in Shivam (Tomcat/Java) as needed. No Oracle driver required. Shivam team writes whatever the import service needs. | Defines the Shivam-side API spec to be agreed with Shivam team before import script is built |

---

## 13. Risk Summary

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Mirth API contract differs from what Shivam docs say | Medium | Export live Mirth configs first (Step 1), don't guess |
| Patient record migration has duplicates/conflicts | High | Run dedup against phone + MRN before migration |
| Python ASTM converters have gaps for some machines | Medium | Test each machine in isolation in staging |
| Historical import incomplete at decommission time | High | Verify last-2-years data fully in ERPNext before decommission gate. Older batches can continue post-cutover. Do not treat decommission as a deadline that cuts import short. |
| Shivam import APIs not ready when import script development starts | Medium | Agree API spec with Shivam team early — list of endpoints, payload shapes, pagination — before writing the Python import service. The spec drives both sides. |
| Historical PDF availability — Neosoft API may not serve all PDFs back to 2013 | Medium | Audit Neosoft PDF API coverage. For gaps, check if iReport output files are retained on Shivam file server. |
| ERPNext Healthcare module gaps need more custom work than estimated | Medium | Prototype Lab Accession doctype early; smoke test before full investment |
| Orthanc MWL format differs between Shivam and labbit_lims push | Low | Orthanc DICOM conformance statement + test with one modality first |

---

*Document status: Draft — for team review before development scoping.*
*Next action: Export Mirth channel configs (Q1). This unblocks Steps 2–4.*

---

## 14. Comparison: Today's Plan vs labit-one (already built)

### What labit-one already has

`labit-one` at `/Users/pav/projects/labit-one` is a **working Frappe custom app** (`labit_core`) with 18 DocTypes designed with full field schemas, permissions, and naming rules. Already built:

- `Labit Requisition` (LAB-YYYY-#####) — the primary operational unit
- `Labit Sample` (SM-YYYY-#####) — physical sample with full chain-of-custody
- `Labit Sample Event` — append-only audit log, immutable after creation
- `Labit Test` + `Labit Test Parameter` + `Labit Reference Range` — test catalog with LOINC codes
- `Labit Organization Profile` — B2B billing, CGHS/ECHS/TPA claim configs
- `Labit Patient External ID` — ABHA, insurance IDs, corporate IDs
- `Labit Barcode Batch` — barcode issuance tracking per phlebotomist
- 3 API endpoints: `search_patients`, `confirm_sample_collected`, `link_sales_invoice`
- NABL-aware design: critical value alerting, delta check, QC module documented (deferred to Phase 2)
- ABDM/ABHA integration planned (deferred)
- Clear 3-phase roadmap with detailed deferred features doc

### What today's plan adds that labit-one doesn't cover

| Gap in labit-one | Today's plan covers |
|-----------------|---------------------|
| Mirth repointing strategy | Config change only — repoint REST channels from Shivam → labit_core |
| Python ASTM→HL7 converter activation | Plug into Mirth as input channels — already built by Labbit team |
| Labbit ↔ ERPNext API bridge | Patient sync, accession creation, result dispatch webhook |
| Webhook dispatcher (ERPNext → Labbit) | Frappe native Webhook doctype on result approval |
| Orthanc MWL feed from ERPNext | push_mwl API in labit_core, study UID back-link to Radiology Order |
| Labbit frontend strategy | Next.js for all patient-facing and field-worker screens |
| Patient identity across systems | `patient_external_keys` mapping to `erpnext_patient_id` |
| Parallel run / decommission path | 30-day parallel run, result parity check before Shivam decommission |

### Key strategic difference: frontend

- **labit-one plan**: React + Vite + Tailwind + shadcn/ui INSIDE Frappe bench (for clinical desk screens)
- **Today's plan**: Labbit (Next.js) calls ERPNext API for all non-finance screens

These are **complementary, not competing**. labit-one's React UI → internal clinical workflow (registration desk, result entry, sample receipt). Labbit Next.js → patient portal, WhatsApp bot, home visit field ops, report dispatch.

### Naming reconciliation

| Today's plan | labit-one actual |
|-------------|-----------------|
| "Lab Accession" | `Labit Requisition` (LAB-YYYY-#####) + `Labit Sample` (SM-YYYY-#####) |
| "labbit_lims" | `labit_core` (the Frappe app) |
| "labbit_lims API surface" | labit_core whitelisted API methods |

### Verdict

**Today's plan is better at:** Integration layer (Mirth, webhooks, Orthanc), Labbit↔ERPNext bridge, migration path from Shivam, frontend ownership strategy.

**labit-one is better at:** DocType schemas (far more detailed), phase structure (clear Phase 1/2/3 with explicit deferred features), regulatory compliance (NABL, ABDM, LOINC, ABHA), internal lab UI.

**Together they form a complete picture.** The right path: continue `labit-one` development (don't start a new app), and layer today's integration architecture on top. Section 5 of this document ("labbit_lims spec") should be **treated as the next sprint of labit-one**, not a separate app.
