# Labit One

**Labit One** is the operational and intelligence layer for diagnostic labs, built on top of ERPNext/Frappe. It owns every workflow a lab actually runs — requisition, sample, result, report, delivery, and communication — while delegating enterprise records (patients, billing, inventory, HR) to ERPNext as the authoritative backbone.

---

## What Labit One Is Not

Labit One is **not** an ERP replacement. It does not maintain its own patient master, billing engine, inventory, or accounting. Those are ERPNext's responsibilities. Labit One extends ERPNext through Frappe's custom app system and calls its APIs — it does not fight the framework or duplicate what ERPNext already owns.

---

## Architecture: Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    ERPNext / Frappe                          │
│  Enterprise backbone: patients, billing, items, HR, roles   │
│  Database: MariaDB 10.6+                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │ Frappe REST API / Python hooks
┌─────────────────────────▼───────────────────────────────────┐
│                     Labit One                                │
│  Operational layer: requisition → sample → result → report  │
│  Backend: Frappe custom app (labit_core)                     │
│  Frontend: React + Vite calling Frappe REST APIs             │
└─────────────────────────┬───────────────────────────────────┘
                          │ optional, Phase 2+
┌─────────────────────────▼───────────────────────────────────┐
│               Labit CTO Engine (Supabase)                    │
│  Technical telemetry only: integration health, HL7 errors,  │
│  uptime monitoring, queue diagnostics                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Product Modules

| Module | Scope |
|---|---|
| **Labit One Diagnostics** | Requisition, sample collection, result ingestion, report workflow |
| **Labit One HomeOps** | Home collection scheduling, phlebotomist dispatch, logistics |
| **Labit One Connect** | WhatsApp bot, WABA sender, patient communication |
| **Labit One Reports** | Result PDF generation, approval workflow, delivery |
| **Labit One Insights** | Patient trends, lab manager dashboards, CEO/management views |
| **Labit One CTO** | Integration health, machine uptime, queue telemetry, HL7 error logs |

---

## Current Build Phase

**Phase 1 — Diagnostics Vertical Slice**

Target: replace the Shivam registration and requisition workflow at SDRC.

Scope: Patient search → Requisition creation → Test selection → Sample collection status → Billing link

Out of scope in Phase 1: result entry, analyzer integration, report generation, WhatsApp delivery, home collection, management dashboards.

---

## Tech Stack

### Enterprise Backbone
- ERPNext v15 / Frappe Framework v15
- MariaDB 10.6+

### Labit One Operational Layer
- **Backend:** Frappe custom app (`labit_core`) — Python, Frappe ORM, Frappe REST API
- **Frontend:** React (Vite) — custom operational screens calling Frappe REST APIs directly
- **UI:** Tailwind CSS + shadcn/ui
- **Data fetching:** React Query
- **Client state:** Zustand

> Standard Frappe form pages are not used for operational screens. Speed and UX control require custom React interfaces.

### Labit CTO Engine (Phase 2+, optional)
- Supabase (Postgres)
- Scoped to: integration health, HL7 error logs, uptime monitoring, queue telemetry

### Communication Services (Phase 2+)
- WhatsApp Business API (WABA) — Labit One Connect module

### Infrastructure
- Docker Compose for local dev (Frappe + MariaDB + Redis)
- Target deployment: single-server initially, designed for multi-tenant

---

## Repo Structure

```
labit-one/
├── README.md
├── setup.py                  # pip-installable Frappe app (bench get-app compatible)
├── requirements.txt
├── labit_core/               # Frappe custom app package
│   ├── hooks.py
│   ├── modules.txt
│   ├── doctype/              # DocTypes (Labit Requisition, Sample, etc.)
│   ├── api/                  # Whitelisted action endpoints
│   └── utils/                # Shared validators and helpers
├── docs/
│   ├── ARCHITECTURE.md       # Ownership boundaries, DocTypes, design principles
│   ├── PRODUCT.md            # Phase 1 product definition and success criteria
│   └── decisions/            # Architecture Decision Records (ADRs)
├── frontend/
│   └── labit-ui/             # React + Vite frontend
├── services/
│   ├── connect/              # WhatsApp/WABA service (Phase 2)
│   └── integrations/         # Machine/HL7 integration service (Phase 2)
├── infra/
│   └── docker/               # Docker Compose configs
└── .github/
    └── workflows/            # CI placeholder
```

---

## Local Dev Setup

> Full setup instructions to be documented once Docker Compose config is scaffolded.

**Prerequisites:**
- Docker + Docker Compose
- Node.js 18+
- Python 3.10+

**Quick start (placeholder):**
```bash
# Clone and enter repo
git clone <repo-url> labit-one && cd labit-one

# Start Frappe + MariaDB + Redis
docker compose -f infra/docker/docker-compose.yml up -d

# Install Frappe app directly from this repo
bench get-app https://github.com/labbit-23/labit-one
bench --site labit.local install-app labit_core

# Start frontend dev server
cd frontend/labit-ui && npm install && npm run dev
```

---

## Docs

- [Architecture](docs/ARCHITECTURE.md) — ownership boundaries, DocTypes, design principles
- [Product — Phase 1](docs/PRODUCT.md) — problem statement, workflow, success criteria
