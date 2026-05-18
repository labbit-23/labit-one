# Report Architecture — Labit One Diagnostics

## Three Report Types

Every `Labit Report Request` has a `report_type` field that determines the data capture model,
the formatting template, and the approval workflow.

---

## Type 1: Grid Layout

**Used for:** Blood tests, urine analysis, biochemistry, haematology, immunology, serology, microbiology sensitivities.

**Structure:**
```
[Lab Header — logo, name, address, NABL number, accreditation scope]
[Patient Strip — name, age, sex, MRN, DOB, sample date, report date,
                 referring doctor, collected by, received at]

  SECTION HEADING (e.g., "Haematology")
  ┌──────────────────┬────────┬──────┬──────────────┬──────┬────────────┐
  │ Parameter        │ Value  │ Unit │ Ref Range    │ Flag │ Method     │
  ├──────────────────┼────────┼──────┼──────────────┼──────┼────────────┤
  │ Haemoglobin      │ 11.2   │ g/dL │ 13.0 – 17.0  │  L   │ Cyanmet    │
  │ RBC Count        │ 3.8    │ M/µL │ 4.5 – 5.5    │  L   │            │
  │ WBC Count        │ 8200   │ /µL  │ 4000 – 11000 │      │            │
  │ AST/ALT Ratio    │ 0.9    │      │ < 1.0        │      │ Calculated │
  └──────────────────┴────────┴──────┴──────────────┴──────┴────────────┘

  SECTION HEADING (e.g., "Biochemistry")
  [next section...]

  [Histogram / Scattergram attachment — per parameter, if applicable]

  IMPRESSION
  [Free text — pathologist's summary statement]

  INTERPRETATION
  [Free text — clinical correlation note, if added]

  HISTORICAL VALUES (optional, toggle per template)
  ┌──────────────────┬────────┬────────┬────────┐
  │ Parameter        │ Today  │ 3m ago │ 6m ago │
  └──────────────────┴────────┴────────┴────────┘

[Signatory block — name, qualification, registration number, signature/stamp]
[Footer — NABL accreditation number, validity, disclaimer]
```

**DocTypes involved:**
- `Labit Report Request` (report_type = Grid)
- `Labit Report Section` (child — one per test section heading)
- `Labit Report Parameter` (child of Section — one per result row)
- `Labit Report Template` (formatting rules — show/hide method, history, ranges)

**Labit Report Parameter fields:**
```
parameter               Link → Labit Test Parameter
value_numeric           Float       (if input_type = Numeric)
value_text              Data        (if input_type = Text)
unit                    Data        (fetched from parameter, overrideable)
reference_range_display Data        (formatted: "13.0 – 17.0" or "Negative")
flag                    Select      Normal / Low / High / Critical Low / Critical High
method                  Data
is_calculated           Check       (read-only flag, fetched from parameter)
attachment              Attach      (histogram, scattergram for this parameter)
```

---

## Type 2: Text Edited

**Used for:** Sonology (USG), X-Ray, Echocardiography, MRI, CT, Mammography, Colour Doppler.

**Structure:**
```
[Lab/Radiology Header]
[Patient Strip + Study Details — modality, clinical indication, machine used]

FINDINGS
[Rich text — structured free text by organ/system, authored by radiologist/sonologist]
Example:
  "LIVER: Normal size and echogenicity. No focal lesion.
   GALL BLADDER: Normal. No calculi.
   RIGHT KIDNEY: 10.2 cm. Normal corticomedullary differentiation..."

IMPRESSION
[Separate free text — the conclusion/diagnosis]
Example:
  "No significant abnormality detected on sonography of abdomen and pelvis."

[Image attachments — JPG/PNG or DICOM reference]

[Signatory — Radiologist/Sonologist name, qualification, registration]
```

**DocTypes involved:**
- `Labit Report Request` (report_type = Text Edited)
- No section/parameter child tables — findings and impression are Long Text fields
- `Labit Report Attachment` (child — images, cine clips)

**Key difference from Grid:** The result IS the text. No parameters, no reference ranges, no flags.
The doctor authors the report directly — it is not auto-generated from entered values.

**Approval workflow:** Radiologist drafts → senior radiologist reviews (optional, configurable per department) → approves → released.

---

## Type 3: Direct PDF Attached

**Used for:** ECG, BMD/DEXA, Pulmonary Function Test (PFT), Audiometry, Nerve Conduction Study (NCS),
and selected outsourced tests where the reference lab provides their own formatted report.

**Structure:**
```
[Labit Cover Page — lab header + patient strip + accession number]
[Machine-generated PDF — attached as-is]
[Interpretation Note — optional short text by cardiologist/pathologist]
[Signatory]
```

**DocTypes involved:**
- `Labit Report Request` (report_type = Direct PDF)
- `machine_pdf` Attach field — the PDF from the machine or reference lab
- `interpretation_note` Text — the clinician's added note (brief, not a full findings section)

**Approval workflow:** Tech uploads machine PDF → clinician adds interpretation note → approves → system
merges cover page + machine PDF + interpretation into final deliverable PDF.

**Note:** BMD/DEXA reports from the GE Lunar machine are already handled in the `sdrc-dexa` system.
When Labit One takes over that workflow, the XPS → PDF extraction logic from `sdrc-dexa` will be
integrated here as the machine PDF source for Direct PDF type reports.

---

## Approval Workflow — All Types

```
                  DRAFT
                    ↓
            [Tech/Sonologist enters results or uploads PDF]
                    ↓
           PENDING APPROVAL
                    ↓
            [Pathologist / Radiologist reviews]
            [Critical alerts acknowledged?]  ← must clear before approval
            [Delta checks resolved?]         ← must clear before approval
                    ↓
               APPROVED
                    ↓
            [Report PDF generated / merged]
                    ↓
               RELEASED
                    ↓  (if error found post-release)
             AMENDMENT PROCESS
                    ↓
            [New version created, original retained]
             AMENDED (v2 released, v1 superseded)
```

**Role → action matrix:**

| Action | Lab Technician | Lab Manager | Pathologist | Radiologist |
|---|---|---|---|---|
| Enter results (Grid) | ✅ | ✅ | ✅ | — |
| Draft report (Text Edited) | — | — | ✅ (path) | ✅ (rad) |
| Upload machine PDF | ✅ | ✅ | — | — |
| Add interpretation note | — | — | ✅ | ✅ |
| Approve | — | ✅ | ✅ | ✅ |
| Release | — | ✅ | ✅ | ✅ |
| Amend post-release | — | ✅ | ✅ | ✅ |

---

## Report Template DocType

Controls visual formatting — one template per department or per client.

```
template_name               Data
report_type                 Select: Grid / Text Edited / Direct PDF
applicable_departments      child table (which departments use this)
applicable_organizations    child table (org-specific letterhead — CGHS, corporate)

# Grid-specific display options:
show_method                 Check, default 1
show_reference_range        Check, default 1
show_history                Check, default 0
history_result_count        Int, default 2
show_histogram_inline       Check, default 1
flag_style                  Select: Text (H/L) / Colour / Arrow / Symbol

# Branding:
lab_logo                    Attach
header_html                 HTML
footer_html                 HTML
signatory_format            Select: Name Only / Name + Qualification / With Stamp
custom_css                  Code (CSS overrides)
watermark_draft             Data  "PRELIMINARY — NOT FOR CLINICAL USE"
watermark_amended           Data  "AMENDED REPORT"
```

---

## DocTypes to Build (Phase 2)

```
Labit Report Section          child of Labit Report Request (Grid type)
Labit Report Parameter        child of Labit Report Section (one per result row)
Labit Report Attachment       child of Labit Report Request (images, PDFs)
Labit Report Template         formatting rules per department/client
```

`Labit Report Request` already exists in the schema (Phase 1). It needs `report_type`,
`impression`, `interpretation`, `findings` (Text Edited), `machine_pdf` (Direct PDF),
and `interpretation_note` fields added when Phase 2 begins.
