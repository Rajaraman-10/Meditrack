# MediTrack

MediTrack is a clinic management system built incrementally with React, Django REST Framework, and MySQL.

## Local development setup

### Requirements

- Node.js 20.19+ and npm
- Python 3.13
- MySQL Community Server for MySQL-backed development

### Backend

From the project root, create and activate a virtual environment, then install the backend dependencies:

```powershell
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Copy `.env.example` to `.env`. For the initial connection smoke test, leave `DB_ENGINE=sqlite`. To use MySQL, set `DB_ENGINE=mysql` and provide a database name, user, password, host, and port using environment variables.
The default clinic timezone is `Asia/Kolkata`; keep `TIME_ZONE` aligned with the
clinic's local timezone so appointment dates, availability, and check-in use the same
calendar day.

Start the API:

```powershell
Set-Location backend
python manage.py runserver
```

The health endpoint is `http://127.0.0.1:8000/api/health/`.

Run the initial database migrations before creating a development administrator:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

The custom user model is configured before the first migration.

### Authentication API

- `POST /api/auth/register/` creates an active patient account; the server never accepts a role from public registration.
- `POST /api/auth/login/` exchanges email and password for access and refresh tokens.
- `POST /api/auth/refresh/` exchanges a valid refresh token for a new access token.
- `POST /api/auth/logout/` revokes the caller's refresh token.
- `GET /api/auth/me/` returns the authenticated user's safe profile fields.

The frontend stores tokens in `sessionStorage` for this learning-phase setup.
This is convenient for local development, but JavaScript-accessible storage can
be exposed by cross-site scripting. A production deployment should evaluate
HttpOnly, Secure, SameSite cookies and their CSRF requirements.

Email verification is disabled: patient accounts can sign in as soon as registration
succeeds. This does not confirm ownership of the submitted email address, so a user
could register another person's unclaimed address. Do not associate clinical records
with an account based only on an unverified email address.

### Clinic operations API

- `GET /api/patients/` lists all patients for administrators/receptionists and only the signed-in patient's own profile for patients.
- `POST /api/patients/` lets clinic staff register a patient with a temporary password.
- `GET/PATCH /api/patients/{id}/` provides scoped patient-profile access.
- Every patient profile receives a server-generated, unique `MED-000001`-style Patient Number; it is read-only and included in patient registration/profile responses.
- `GET /api/patients/doctor-search/?patient_number=MED-000001` searches for a patient only when the signed-in doctor has a non-cancelled appointment with them; `GET /api/patients/doctor-records/{id}/` returns that doctor's scoped clinical record and audits the access.
- `GET /api/departments/` and `GET /api/doctors/` provide the clinic directory; administrators create and manage these records.
- `POST /api/auth/users/` lets administrators provision receptionist accounts. Doctor accounts are created with their doctor profile.
- `/api/availabilities/` manages recurring weekly doctor hours. Doctors can create,
  change start/end times, and remove only their own hours; clinic staff can manage
  any doctor's schedule.
- `/api/schedule-exceptions/` manages one-day closures or date-specific open hours.
  Doctors can manage exceptions for their own schedule. The doctor availability page
  displays the upcoming 14 calendar dates, applies date overrides, and provides edit
  controls for weekly and date-specific hours.
- `GET /api/doctors/{id}/slots/?date=YYYY-MM-DD` returns open slot start times in the configured clinic timezone.
- `GET/POST /api/appointments/` lists scoped appointments and books a slot. Clinic staff provide a patient ID; patients can book only for themselves.
- `PATCH /api/appointments/{id}/` supports permitted cancellation, confirmation, and staff rescheduling.
- `POST /api/appointments/{id}/check-in/` checks in a same-day appointment and atomically adds it to that doctor's queue.
- `GET /api/queue/?date=YYYY-MM-DD` lists only the caller's authorized queue entries; staff can mark a waiting entry as left or return it to waiting.
- `GET /api/patients/{id}/appointments/` exposes appointment history to the patient themselves or clinic staff.

Appointment booking checks that the requested start time exactly matches a
currently available slot and then checks overlaps again inside a transaction.
MySQL locks the doctor's row during this operation so simultaneous bookings
for that doctor are serialized. SQLite's `select_for_update()` does not provide
that same concurrency guarantee, so production double-booking behavior must be
verified with MySQL.

Doctor slot lengths are configured per doctor (5–240 minutes). Weekly hours
generate slots at that interval; date-specific exceptions override the weekly
hours for the selected date. Set `TIME_ZONE` to the clinic's IANA timezone in
the root `.env`; Django stores appointment datetimes as timezone-aware values.

## Backend layout

- `backend/config/` contains Django settings, root URLs, and project-wide views.
- `backend/apps/` contains domain-focused Django apps for accounts, patients,
  clinics, and appointments.
- The custom account signs in with a unique email and has one role. Django's
  built-in password hashing and permission-group relationships are retained.
- `backend/media/` is the local development upload directory and is ignored by
  Git.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`. The home page checks the backend health endpoint and reports whether it can reach the API.

## Clinical workflows and operations APIs

Run `python manage.py migrate` after pulling model changes. The API and role-specific
frontend workspaces now also include:

- `GET /api/dashboard/` returns server-calculated metrics scoped to the signed-in role.
  Administrator appointment/revenue trends are returned for the analytics charts.
- `GET/POST /api/consultations/` lists authorized clinical records and lets the assigned
  doctor start one for a checked-in appointment. `PATCH /api/consultations/{id}/`
  updates active notes, `/complete/` completes the consultation, and `/notes/` adds a
  time-stamped authored note.
- `GET/POST /api/prescriptions/` lists a patient's own prescriptions or lets the assigned
  doctor create a prescription with one or more medication items during an active
  consultation.
- `GET /api/medicines/?search=para` searches the active medicine catalog by name,
  generic name, and strength. Clinic administrators can manage catalog entries in
  Django Admin.
- Import a clinic medicine CSV with `python manage.py import_medicines <csv-path>`.
  For the provided Windows file, run
  `python manage.py import_medicines C:\Users\Admin\Downloads\meditrack_medicine_database_1000.csv`.
  The import preserves each CSV `medicine_id` as `source_id`, validates required
  columns and field lengths, rejects duplicate products/IDs, and is safe to rerun: it
  updates matching products instead of creating duplicates.
- Prescription items may reference a catalog medicine and include dosage, route,
  frequency, duration, food timing, and instructions. Doctors confirm the patient by
  Patient Number and select one of their completed consultations. Issued prescriptions
  remain payment-pending and are excluded from patient list/detail API responses until
  an authorized billing user releases them after the appointment invoice is paid.
  **View / Download PDF** opens a print-ready template only after release.
- If a confirmed patient has a checked-in appointment but no active consultation, the
  doctor prescription page offers **Start consultation** there. A medicine not yet in
  the catalog can also be entered manually with its name and strength.
- `GET/POST /api/lab-tests/` lets doctors request tests during a consultation.
  `POST /api/lab-tests/{id}/reports/` records a result (optionally linked to a document);
  `POST /api/lab-tests/{id}/review-report/` records a doctor's/admin's review.
- `GET/POST /api/documents/` lists the caller's authorized files and accepts multipart
  uploads. `GET /api/documents/{id}/download/` streams a file only after checking the
  caller's role and patient/doctor relationship. PDF/JPG/PNG uploads are limited to
  10 MB and stored under randomized names in local `backend/media/`.
- `GET/POST /api/invoices/` lets clinic staff create draft invoices with multiple
  charge lines and an optional discount. Admin, receptionist, and Billing roles can
  transition drafts to issued/void and issued invoices to paid (recording a counter
  payment method and optional reference) with `POST /api/invoices/{id}/status/`.
  Patients can read only their own invoices. Staff and patients can view and print
  invoices from the same signed-in browser tab. No online payment provider is connected.
- Admin-only `GET/POST /api/auth/users/`, `PATCH /api/auth/users/{id}/`, and
  `POST /api/auth/users/{id}/reset-password/` support non-admin staff provisioning,
  profile/status changes, and password resets (existing refresh tokens are blacklisted).
  Public registration continues to create patient accounts only. Department codes are
  stored in the department table; only administrators can create, edit, or deactivate
  departments.
- `GET /api/invoices/unbilled-appointments/` gives authorized clinic and Billing staff
  only the minimal patient/visit details needed to create an invoice, without granting
  Billing users general appointment-management access.
- `GET /api/prescriptions/release-queue/` exposes only release metadata to Billing and
  Admin. `POST /api/prescriptions/{id}/release/` checks the related appointment invoice
  on the server and refuses release until it is marked paid. Previously created
  prescriptions are grandfathered as released by the migration.
- `GET /api/notifications/` and the `/read/` and `/read-all/` actions provide
  recipient-scoped in-app notification access.
- `GET /api/audit-logs/` is restricted to administrators and exposes recorded,
  append-only activity events.

The frontend provides role-aware consultation, prescription, laboratory, document,
billing, notification, activity-log, and dashboard pages. Recharts is loaded only with
the analytics page so it does not inflate the initial application bundle.

## Clinical data and file safety

Consultations, prescriptions, laboratory records, invoices, and files are linked back to
the appointment/patient context. The API checks ownership/assignment on every read and
write; hiding a link in React is not authorization. Uploaded medical files are not
exposed through Django's public development media URL. The application streams them
through an authenticated download endpoint instead.

Local media storage is for development only. Before deployment, use storage with
private-by-default access, authenticated delivery, encrypted backups, retention rules,
and malware/content inspection appropriate to the clinic. The file-extension allowlist
and size limit are not a substitute for those controls.

The notification workflow is synchronous and in-app for this stage. Redis, Celery,
WebSockets, Docker, and cloud hosting have intentionally not been added: the current
features do not need a separate queue, live push channel, or container runtime to work.
Revisit them when actual delivery volume, latency, or deployment requirements justify
the additional operations burden.

## Verification and deployment preparation

Run the backend checks and tests from `backend/`:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Run the frontend checks from `frontend/`:

```powershell
npm run lint
npm run build
```

Before deploying:

1. Configure a unique secret, production database credentials, allowed hosts, HTTPS
   origins, and the clinic timezone through environment variables; do not deploy the
   sample `.env.example` values.
2. Validate the schema and appointment-locking behavior against MySQL. SQLite is useful
   for local setup but cannot certify concurrent double-booking prevention.
3. Decide on a production token-storage strategy. The current browser `sessionStorage`
   implementation is for learning and is not a substitute for a production XSS/CSRF
   review.
4. Configure private document storage, access-controlled backups, retention, monitoring,
   and restore procedures. Never publish the local `MEDIA_ROOT`.
5. Run the security review and the full backend/frontend test suite against the final
   deployment configuration before accepting patient data.

## Configuration and secrets

Never commit `.env` or `frontend/.env.local`. `.env.example` files document the required setting names without containing real credentials. Use a unique, securely generated Django secret key for any environment beyond local development.
