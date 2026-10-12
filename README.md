# DiaCare Voice

A bilingual (Tamil/English) voice-first chatbot that guides people with type 2 diabetes through a guideline-anchored self-care program: a 3-sitting baseline assessment, a personalized Care Plan, and a 12-week weekly check-in — with continuous safety monitoring running underneath all of it.

Clinical content is anchored to the **ICMR Guidelines for Management of Type 2 Diabetes (2018)** and the **AADE7 Self-Care Behaviours** framework. This is a prototype, not a certified medical device — see [Disclaimer](#disclaimer).

## Disclaimer

DiaCare is not a doctor. It never initiates, changes, or stops a medicine or dose. It is a self-care coaching aid intended to support — not replace — the guidance of a treating clinician. It has not undergone a clinical trial or regulatory review. Do not use it as a substitute for professional medical advice, diagnosis, or treatment.

## Architecture

The system is split into three layers, deliberately kept independent:

```
Patient Browser (React PWA)
        │  fetch /api/*  (JSON)
        ▼
┌─────────────────────────────────────────────┐
│  FastAPI backend                             │
│                                               │
│   Routers/API ──► Rule Engine  (deterministic│
│        │           Python — sole author of   │
│        │           clinical content)         │
│        │                                     │
│        └────────► Speech Proxy ──► Sarvam AI │
│                    (ASR/TTS only — never     │
│                     authors clinical text)   │
└─────────────────────────────────────────────┘
        │
        ▼
   PostgreSQL
```

**The one rule the architecture is built around:** the language model / speech layer (Sarvam AI, used only for automatic speech recognition and text-to-speech) has no path to the Rule Engine. It converts already-authored text to speech and raw audio to a transcript — it cannot originate a sentence of clinical advice. Every question, risk flag, and Care Plan line is produced by a deterministic function in `backend/services/*_engine.py`, independently unit-tested.

## Modules

| Module | Name | Collects | Key logic |
|---|---|---|---|
| **A** | Onboarding & Consent | Language, consent, check-in time preference | Consent gate; sets the 3-sitting schedule |
| **B1** | Basic Profile | Demographics, body measures, occupation | Asian-Indian BMI cut-offs, waist risk, ideal body weight, sedentary-work flag |
| **B2** | Diabetes Profile | History, labs, BP, medications, screening dates | ICMR glycaemic bands, regimen classification, overdue-screening flags |
| **B3** | Risk & Complication Screening | Feet, eyes, kidney, heart, tobacco, alcohol | Foot-risk tier, exercise-clearance flag, composite risk tier (red/amber/green) |
| **M1** | Healthy Eating | Meals, rice, veg, salt, snacks | Exactly two diet goals chosen from the largest gaps |
| **M2** | Being Active | Activity days, strength/yoga | Graded activity ramp, downgraded by B3 complication flags |
| **M3** | Taking Medication & Monitoring | Adherence, missed-dose barrier, target knowledge | Target numbers graded against real ICMR ranges (not self-reported) |
| **M4** | Healthy Coping & Problem Solving | Hypo symptoms, sleep, mood screen | 15-15 hypoglycaemia protocol, 2-item mood screen (no diagnosis made) |
| **C** | Weekly Check-In | 8 items, repeated for 12 weeks | Per-domain progression/regression; 2 consecutive poor weeks trigger reassessment |
| **D** | Safety Monitoring | Runs continuously across every module | Red-flag detection opens a safety event; the server answers every coaching endpoint with HTTP 423 + the fixed emergency script until a clinician acknowledges it on the dashboard |

Full question list, decision rules, and worked example: see the conversation history in this repo's project notes, or the ICMR/AADE7-anchored spec this build follows.

## Tech stack

| | |
|---|---|
| Frontend | React 19, Vite, TypeScript, Zustand, installable PWA with service worker |
| Backend | FastAPI, SQLAlchemy 2.x (async), Pydantic v2 |
| Database | PostgreSQL (production), SQLite (local dev) |
| Speech | Sarvam AI — ASR + TTS, Tamil and English |
| Frontend hosting | Netlify |
| Backend hosting | Render (web service + managed Postgres) |
| Scheduling | GitHub Actions cron → `POST /api/scheduler/daily-tick` (drives the 12-week check-in cadence) |

## Project structure

```
diacare/
├── backend/
│   ├── main.py                  # FastAPI app, router registration
│   ├── config.py                # Settings (DATABASE_URL, Sarvam/VAPID keys)
│   ├── database.py              # Async SQLAlchemy engine/session
│   ├── models/                  # ORM models (users, conversation, baseline_profile, care_plan, checkin, safety_event, ...)
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── routers/                 # API endpoints (conversation, care_plan, checkin, admin, speech, scheduler, ...)
│   ├── services/                # Deterministic decision engines: b1/b2/b3/m1/m2/m3/m4_engine.py,
│   │                             #   checkin_engine.py, safety_engine.py, care_plan_generator.py,
│   │                             #   audio_generation.py, backup_service.py
│   ├── data/questionnaires/     # diafit_voice_baseline.json — the single source of truth for every question asked
│   ├── scripts/                 # seed_admin.py, backup_db.py, migrate_to_postgres.py, etc.
│   └── tests/test_decision_engine.py
├── frontend/
│   ├── src/
│   │   ├── pages/               # Route-level screens (Home, Conversation, CarePlan, CheckIn, AdminDashboard, ...)
│   │   ├── components/          # assessment/, careplan/, common/, voice/, home/, registration/
│   │   ├── domain/               # types.ts, conversationEngine.ts (script parsing/validation)
│   │   ├── stores/               # Zustand stores (user, conversation, voice coach)
│   │   ├── services/             # api/ (backend client), speech/, push/, storage/ (local IndexedDB, prefs only)
│   │   └── data/translations.ts # English + Tamil UI strings
│   └── public/                  # manifest, service worker, icons
├── render.yaml                  # Render Blueprint (backend + Postgres)
├── netlify.toml                 # Netlify build config
└── .github/workflows/           # daily-checkin-tick.yml
```

## Getting started

### Prerequisites

- Python 3.13+ and a virtual environment (`backend/.venv` if already created)
- Node.js 18+ and npm
- (Optional) a Sarvam AI API key for live voice — the app works fully with touch/text input without one

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1        # or: python -m venv .venv; then activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

SQLite is used by default (`./diafit.db`, auto-created on first run) — no migration step needed for local dev. To use Postgres instead, set `DATABASE_URL` (see below).

### Frontend

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to http://localhost:8000
```

### Environment variables (backend `.env`)

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | No (defaults to local SQLite) | `postgresql+asyncpg://...` for Postgres. A bare `postgres://` or `postgresql://` URL (e.g. from Render) is auto-normalized to the asyncpg driver. |
| `SARVAM_API_KEY` | No | Enables live speech recognition/synthesis. Without it, voice features degrade gracefully to touch/text input. |
| `SARVAM_BASE_URL` | No | Defaults to `https://api.sarvam.ai` |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_CLAIM_EMAIL` | No | Enables Web Push notifications (check-in/medication reminders) |

### Environment variables (frontend)

| Variable | Required | Purpose |
|---|---|---|
| `VITE_API_URL` | No in local dev (proxy handles it); **yes in production** | Origin of the deployed backend, e.g. `https://your-backend.onrender.com` |

### Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

`tests/test_safety_lock.py` covers the server-side Module D lock end to end (API + an isolated SQLite DB per test).

All decision-engine logic (BMI/risk classification, glycaemic bands, activity ramps, barrier classification, target-knowledge grading, check-in progression, safety triggers) is covered by unit tests independent of the API/database layer.

## Deployment

- **Backend + Postgres**: `render.yaml` defines a Render Blueprint — push to GitHub, then "New → Blueprint" on Render pointed at this repo provisions both automatically.
- **Frontend**: `netlify.toml` configures the build (`npm run build`, publish `frontend/dist`) and the SPA redirect. Set `VITE_API_URL` in Netlify's environment variables to the Render backend's URL.
- **Weekly check-in scheduler**: `.github/workflows/daily-checkin-tick.yml` runs daily and calls `POST /api/scheduler/daily-tick`, which advances the 12-week check-in cadence and sends due reminders. Render's free tier has no built-in cron, so this workflow is what actually drives it — without it, check-ins never fire.
- **Safety-event migration** (once, on any database created before the coaching lock): `python scripts/migrate_add_safety_event_status.py` adds `status`, `acknowledged_by` and `acknowledgement_note` to `safety_events`. Every existing unresolved event becomes `open` and locks that patient until acknowledged — review the dashboard's Safety Events tab right after running it.
- **Seeding the admin account** (once, after first deploy): `POST /api/admin/seed` creates `admin` / `diafit2024`. Change the password immediately via the Admin Dashboard's Backend tab → Change Password.

## Admin dashboard

Available at `/admin` (login) → `/admin/dashboard`. Provides:

- Overview metrics (users, risk-tier distribution, open safety events, check-in completion)
- Safety Events queue: every open Module D event, with a required note to **acknowledge & unlock** the patient
- User list/detail with baseline profile, care plans, check-ins, safety events
- CSV export of all assessment responses and all weekly check-ins (admin sees every user, since all data lives in one shared Postgres instance)
- Audio-asset generation status, manual backup trigger, temporary-audio cleanup
- Password change

## Known limitations

- No clinical trial or real-world patient outcome data yet — this is a functional prototype, evaluated by unit tests and end-to-end verification, not a clinical study.
- Foot-risk classification currently produces three reachable tiers where the source guideline implies four.
- Activity guidance gives one generic "medical clearance" note rather than differentiating retinopathy- and cardiac-specific restrictions.
- Recurrent hypoglycaemia episodes are not yet auto-escalated across check-ins.
- Personalization is entirely rule-based; there is no machine-learning component.

## Clinical references

- Indian Council of Medical Research. *ICMR Guidelines for Management of Type 2 Diabetes 2018.* New Delhi: ICMR; 2018.
- Kolb L, et al. An Effective Model of Diabetes Care and Education: Revising the AADE7 Self-Care Behaviors®. *The Diabetes Educator.* 2020;46(2):139–160.
