# Labit One — Product Definition

**Phase 1: Diagnostics Vertical Slice**
**Status: Active Build**

---

## Problem Statement

Indian diagnostic labs running on legacy systems — Shivam, LIS spreadsheets, or poorly configured ERPs — lack a fast, connected operational layer. The result is predictable:

- Front desk operators register patients in one system, billing happens in another, sample tracking happens on paper or not at all.
- Phlebotomists have no live view of what is collected and what is pending.
- Lab technicians receive samples with no digital trail back to the requisition.
- Lab managers have no reliable view of daily volume, pending results, or turnaround times.
- Errors propagate silently: wrong test ordered, sample collected under wrong patient, report delivered to wrong contact.

**Labit One Diagnostics** replaces this disconnected operational layer with a single, fast, auditable workflow — from registration through sample receipt — built on top of ERPNext/Frappe as the enterprise backbone.

---

## What Phase 1 Replaces

**At SDRC:** The Shivam registration and requisition workflow.

Shivam is the incumbent LIS. In Phase 1, Labit One replaces only the front-of-house registration and requisition flow. Shivam may continue to run in parallel for result entry and reporting until those modules are built.

The replacement is complete when a front desk operator can register a patient, create a requisition with tests, mark sample collected, and see a linked invoice — entirely within Labit One, without touching Shivam or paper.

---

## Users in Scope — Phase 1

| Role | Primary Responsibility | Key Actions in Phase 1 |
|---|---|---|
| **Front Desk / Registration Operator** | Patient intake, requisition creation, billing | Patient search/create, test selection, requisition save, invoice link |
| **Phlebotomist / Sample Collection Staff** | Tube labelling, collection, accession | Mark sample collected, print barcode/accession label |
| **Lab Technician (Receiving)** | Sample receipt at lab bench | Mark sample received, flag rejections |
| **Lab Manager / Supervisor** | Oversight, exception handling | View daily requisitions, pending samples, sample status |

---

## Core Workflow — Phase 1

```
1. Registration
   └── Search existing patient (name / phone / DOB / MRN)
   └── Or: create new patient via ERPNext Patient API

2. Requisition
   └── Select tests / packages from ERPNext Item catalogue
   └── Create Labit Requisition linked to patient
   └── Generate requisition reference number

3. Sample Collection
   └── Mark sample(s) collected
   └── Create Labit Sample with accession number
   └── Print barcode label
   └── Log Labit Sample Event (collected)

4. Billing Link
   └── Link existing Sales Invoice from ERPNext
   └── Or: trigger invoice creation via ERPNext API

5. Sample Receipt (lab side)
   └── Receive sample against accession number
   └── Log Labit Sample Event (received)
   └── Flag rejected samples with reason
```

---

## Out of Scope — Phase 1

The following are explicitly excluded from Phase 1. They are planned for later phases but must not be partially built or stubbed in ways that create technical debt.

| Capability | Phase |
|---|---|
| Result entry and validation | Phase 2 |
| Analyzer / machine integration | Phase 2 |
| Report PDF generation | Phase 2 |
| Report approval workflow | Phase 2 |
| WhatsApp delivery of reports | Phase 2 |
| Home collection scheduling | Phase 2 |
| Patient trend reports | Phase 3 |
| Management dashboards | Phase 3 |
| Multi-client / multi-tenant | Phase 3 |

---

## Success Criteria — Phase 1

Phase 1 is complete when all of the following are true at SDRC:

1. A front desk operator can search for an existing ERPNext patient by name, phone, DOB, or MRN and get results in under 200ms.
2. A front desk operator can create a new patient through the Labit One screen without opening ERPNext.
3. A front desk operator can select tests or packages from the ERPNext Item catalogue and save a `Labit Requisition` linked to the patient.
4. A phlebotomist can mark a sample as collected on the requisition and see an accession number generated.
5. A `Labit Sample Event` record is written for every collection and receipt action — no state change is unlogged.
6. A lab technician can mark a sample received against its accession number.
7. Each requisition displays a linked ERPNext Sales Invoice or shows a clear action to create one.
8. No Shivam interaction is required for any step above.
9. No paper is required for any step above.

---

## Non-Goals (permanent)

- Labit One is not a billing engine. Invoice creation and payment collection remain in ERPNext.
- Labit One does not maintain its own patient master. The ERPNext Patient record is always the source of truth.
- Labit One does not replace ERPNext's role and permissions system. Access control uses ERPNext User and Role.
- Labit One does not expose a public patient portal in Phase 1.

---

## Assumptions

- ERPNext v15 is installed and configured with patient records, item catalogue (tests/packages), and branch/company structure before Labit One Phase 1 goes live.
- SDRC staff will be trained on the new screens. Change management is out of scope for this document.
- Shivam may run in parallel during transition. Data migration from Shivam to ERPNext Patient is a prerequisite task, not part of Labit One Phase 1 build scope.
