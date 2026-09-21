# Shri Gouri Engineers — Project Management Portal

A Django application for **Shri Gouri Engineers**, a precision CNC/VMC
manufacturing company. It comprises a public company website, an admin project
management system, and a client-facing project tracking portal that installs
as an app from Chrome.

- Database: **MySQL 8** (PostgreSQL and SQLite also supported by configuration)
- Installable **Progressive Web App** on Android and desktop Chrome
- All configuration and credentials in environment variables

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Local setup](#local-setup)
- [Database setup](#database-setup)
- [Environment variables](#environment-variables)
- [Running the tests](#running-the-tests)
- [Installing as an app from Chrome](#installing-as-an-app-from-chrome)
- [Deployment](#deployment)
- [Free test deployment](docs/DEPLOY_FREE.md)
- [Access URLs](#access-urls)
- [Troubleshooting](#troubleshooting)

---

## Features

### Public website
- Home page with services, machines, industries and calls to action
- About, Services, Industries, Machines, Our Work and Contact pages
- Contact form, rate limited, saved to the database and emailed to the office

### Admin dashboard
- Manage clients: create, edit, reset password, view project history
- Manage machines (CNC, VMC, BMC, lathe inventory)
- Create and manage manufacturing projects
- Advance process stages (Material Received → Cutting → … → Completed)
- Upload drawings and files; raise GST invoices with a downloadable PDF
- Per-project activity log
- Analytics: project counts by month and status, top clients, average rating
- Manage the public gallery, services list, custom project fields and stage
  templates
- Enquiry inbox with reply-by-email

### Client portal
- Clients see only their own projects
- Dashboard with project cards and progress bars
- Project detail with the manufacturing timeline and live stage indicators
- Download drawings, invoices and a project timeline PDF
- Star rating and review once a project completes
- In-app and email notifications

### REST API
Session-authenticated, read-only, filtered by role.

```
GET /api/projects/                    list (admin: all, client: own)
GET /api/projects/{id}/               detail, including stages
GET /api/projects/{id}/processes/     stages only
GET /api/projects/?status=completed   filter by status
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework |
| Database | MySQL 8 via PyMySQL (PostgreSQL/SQLite selectable by env var) |
| Frontend | Django templates, Tailwind (CDN), Alpine.js |
| Auth | Django auth with a custom user model and email OTP verification |
| PWA | `django-pwa` routes, project-owned manifest and service worker |
| Static files | WhiteNoise, hashed filenames in production |
| PDFs | ReportLab |
| Email | SMTP, or the console backend in development |
| Serving | Gunicorn |

---

## Project structure

```
shri_gouri_engineers/
├── config/
│   ├── settings.py            All settings, read from the environment
│   ├── env.py                 Dependency-free .env loader and typed getters
│   ├── context_processors.py  Company details available to every template
│   └── urls.py                Root URLs and error handlers
├── apps/
│   ├── core/                  Shared, model-free helpers
│   │   ├── decorators.py      @admin_required, @client_required
│   │   ├── validators.py      Upload size and type checks
│   │   └── views.py           PWA manifest, error pages
│   ├── accounts/              Custom user, OTP auth, client management
│   ├── machines/              Machine inventory
│   ├── projects/              Projects, stages, files, bills, API, PDFs
│   ├── notifications/         In-app and email notifications
│   ├── website/               Public pages and enquiry inbox
│   ├── portfolio/             Work samples and services
│   └── formbuilder/           Admin-defined fields and stage templates
├── templates/
│   ├── base.html              Global shell
│   ├── manifest.json          Web app manifest (overrides django-pwa)
│   ├── pwa.html               PWA meta and service worker registration
│   ├── offline.html           Offline fallback page
│   ├── errors/                400, 403, 404, 500
│   └── partials/              Dashboard shell, pagination
├── static/
│   ├── css/app.css            Component styles
│   ├── js/app.js              Install prompt, loading states
│   ├── js/serviceworker.js    Service worker
│   └── icons/                 PWA icons (generated)
├── tools/generate_icons.py    Regenerates the icon set
├── db/setup_mysql.sql         Creates the database and application user
├── docs/DATABASE.md           Schema, ER diagram, indexes, constraints
├── docs/DEPLOY_FREE.md        Free HTTPS test deployment, step by step
├── render.yaml                Render blueprint for the free deployment
├── tests/test_smoke.py        68 tests covering pages, access rules, PWA
├── docker-compose.yml         Optional MySQL + app
└── .env.example               Every supported setting, documented
```

---

## Local setup

Requires **Python 3.12** and **MySQL 8**.

### 1. Create a virtual environment

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

> The `venv/` directory committed previously points at a Python 3.14
> installation that is not present and cannot be activated. Create a fresh one
> as above; `.venv/` is git-ignored.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env`

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Generate a secret key and paste it into `.env` as `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Set `DB_PASSWORD` to the password you choose in the next step.

### 4. Set up the database

See [Database setup](#database-setup) below, then:

```bash
python manage.py migrate
python manage.py seed_data
```

### 5. Run

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/.

`seed_data` creates:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Client | `abc_industries` | `client123` |
| Client | `xyz_engineering` | `client123` |
| Client | `delta_auto` | `client123` |

Plus 5 machines and 6 projects at various stages. Re-seed from clean with
`python manage.py seed_data --clear`.

**Change these passwords before the site is reachable by anyone else.** They
are development fixtures.

### Running with no database server

To get the app up before MySQL is ready, set `DB_ENGINE=sqlite` in `.env` and
run the migrate/seed/runserver steps as above. Suitable for a look around, not
for real use.

---

## Database setup

### Option A — MySQL already installed (recommended)

Edit `db/setup_mysql.sql` and replace `CHANGE_ME` with a password of your own,
then run it as a MySQL administrator:

```bash
mysql -u root -p < db/setup_mysql.sql
```

```powershell
# Windows, if mysql is not on PATH
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < db\setup_mysql.sql
```

That creates the `sge_portal` database (utf8mb4) and an `sge_app` user with
rights on it and on the test database. Put the same password in `.env` as
`DB_PASSWORD`, then:

```bash
python manage.py migrate
python manage.py seed_data
```

### Option B — MySQL in Docker

Set `DB_PASSWORD` and `MYSQL_ROOT_PASSWORD` in `.env`, then:

```bash
docker compose up -d db        # database only; run the app from the host
docker compose up -d           # database and application together
```

The database is published on `127.0.0.1:3306`, so MySQL Workbench connects to
it in the same way.

### Verifying and inspecting

```bash
python manage.py dbshell       # MySQL client, already connected
python manage.py showmigrations
```

`docs/DATABASE.md` documents the full schema, the ER diagram, every index and
constraint and why it exists, and how to browse the database in MySQL
Workbench, pgAdmin-equivalent clients or the command line.

### Migration commands

```bash
python manage.py makemigrations       # after a model change
python manage.py migrate              # apply
python manage.py migrate projects 0003   # roll back one migration
python manage.py sqlmigrate projects 0004   # show the SQL without running it
```

---

## Environment variables

Full list with comments in `.env.example`. `.env` is git-ignored; real
environment variables always override it, so the same code runs in
development, staging and production.

### Required

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Mandatory when `DEBUG=False`; startup fails without it |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Required unless `DB_ENGINE=sqlite` |
| `ALLOWED_HOSTS` | A wildcard is rejected when `DEBUG=False` |

### Commonly set

| Variable | Default | Notes |
|---|---|---|
| `DEBUG` | `False` | Never `True` on a public host |
| `DB_ENGINE` | `mongodb` | `mongodb`, `mysql`, `postgresql` or `sqlite` |
| `MONGODB_URI` | unset | Required when `DB_ENGINE=mongodb`; the full connection string |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | |
| `DB_SSL_CA` | unset | CA file path; required by managed MySQL providers |
| `SCRIPT_PREFIX` | empty (domain root) | Set to `/web` to serve under a sub-path |
| `SITE_URL` | `http://127.0.0.1:8000` | Used for links in outgoing email |
| `CSRF_TRUSTED_ORIGINS` | empty | Needed once on HTTPS, and for tunnelled PWA testing |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | empty | For Gmail, a 16-character App Password |
| `COMPANY_EMAIL` | empty | Where contact enquiries are sent |
| `COMPANY_GSTIN`, `COMPANY_ADDRESS`, `COMPANY_PHONE` | empty | Printed on invoice PDFs |
| `MAX_UPLOAD_SIZE_MB` | `10` | Per-file upload cap |
| `PAGE_SIZE` | `20` | Rows per page in list views |
| `LOG_LEVEL` / `LOG_TO_FILE` | `INFO` / on when not debugging | Rotating logs in `logs/app.log` |

With `DEBUG=True` the console email backend is selected automatically, so no
SMTP credentials are needed locally — messages print to the terminal.

---

## Running the tests

```bash
python manage.py test tests
```

68 tests covering every page, the admin/client access rules, project isolation
between clients, the stage workflow, validation, the model-level rules, the
REST API, and the PWA manifest and service worker.

The suite runs against whatever `DB_ENGINE` is configured, so a database server
has to be reachable. Django creates a separate test database — `test_` plus
`DB_NAME` — and drops it afterwards, so the working data is never touched. The
configured account needs rights to create and drop that database.

There is no SQLite shortcut: the migrations use MongoDB ObjectId primary keys,
which SQLite has no column type for. To run the suite without reaching for the
shared cluster, point `DB_ENGINE`/`MONGODB_URI` at a local `mongod`.

---

## Installing as an app from Chrome

The portal is a Progressive Web App. Chrome offers installation once four
conditions hold: HTTPS (or `localhost`), a valid manifest, 192px and 512px
icons, and a registered service worker with a fetch handler. All four are in
place.

When Chrome confirms the app is installable, an **Install App** button appears
in the sidebar and the public navigation, and a one-time banner appears at the
bottom of the page. Both are hidden until the browser says installation is
possible, so neither is ever a button that does nothing.

### Desktop Chrome

1. Open the site — `http://127.0.0.1:8000/` is treated as a secure origin, so
   this works locally without HTTPS.
2. Either click **Install App** in the page, or use the install icon (a monitor
   with a downward arrow) at the right-hand end of the address bar.
3. Alternatively: **⋮ menu → Cast, save and share → Install page as app**.
4. Confirm **Install**. The app opens in its own window with no address bar and
   is added to the Start menu, Dock or Applications list.

To verify: **F12 → Application** tab.
- **Manifest** — name, icons, scope and start URL, with no errors listed
- **Service workers** — status "activated and is running"
- **Cache storage** — an `sge-v1-static` cache containing the offline page and
  the icons
- **Lighthouse → Progressive Web App** audit also works

### Android Chrome

The phone must reach the site over **HTTPS** with a certificate the phone
trusts. A plain `http://192.168.x.x:8000` address will not offer installation —
only `localhost` is exempt from the HTTPS requirement.

**Over the local network, using a tunnel:**

1. Run the server on the machine: `python manage.py runserver 0.0.0.0:8000`
2. Expose it over HTTPS with a tunnel, for example
   `ngrok http 8000` or `cloudflared tunnel --url http://localhost:8000`
3. Add the tunnel's hostname to `.env`:
   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
   CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app
   ```
   Restart the server.
4. Open the `https://…` address in Chrome on the phone.
5. Tap **Install App** in the page, or **⋮ menu → Add to Home screen → Install**.
6. Confirm. The icon appears on the home screen and the app opens full screen
   with no browser chrome.

**In production**, once the site is on HTTPS at its real domain, steps 1–3 are
unnecessary: open the site in Chrome on the phone and use
**⋮ → Add to Home screen**.

### What works offline

Static assets are cached, **application data is never cached**. Opening the
app without a connection shows a branded offline page that reloads itself when
connectivity returns; it does not show a stale dashboard. This is deliberate:
every page in the app is account-specific, and a cached dashboard could
otherwise be shown to the next person to open the app on a shared phone, or
after the project has moved on. Project pages, files, invoices and
notification counts always come from the network.

### After deploying an update

The service worker activates the new version immediately rather than waiting
for every tab to close. Bump `CACHE_VERSION` in
`static/js/serviceworker.js` when static assets change in a way that must
retire the old cache.

---

## Deployment

### Checklist

```bash
DEBUG=False
SECRET_KEY=<a strong random value, not the development one>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
SITE_URL=https://yourdomain.com
DB_HOST=<database host>
DB_PASSWORD=<database password>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=<smtp user>
EMAIL_HOST_PASSWORD=<smtp password>
COMPANY_EMAIL=<where enquiries should arrive>
```

With `DEBUG=False` the application automatically enables HTTPS redirection,
HSTS, secure session and CSRF cookies, `X-Frame-Options: DENY`, nosniff and a
same-origin referrer policy. It also refuses to start if `SECRET_KEY` is
missing or `ALLOWED_HOSTS` contains a wildcard.

```bash
python manage.py check --deploy      # Django's own audit
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### Free deployment for testing

To get a shareable HTTPS URL at no cost — Aiven free MySQL plus a Render free
web service, which is also what `render.yaml` and `.python-version` are for —
follow **`docs/DEPLOY_FREE.md`**.

### Recommended stack

```
Nginx (TLS termination)
  └── Gunicorn → Django
        ├── MySQL 8
        └── media/ on disk or object storage
```

Nginx must pass `X-Forwarded-Proto: https`; the application reads it to detect
the original scheme, and without it the HTTPS redirect can loop.

**HTTPS is not optional here** — it is required both for the security settings
above and for Chrome to offer installation at all.

### Serving under a sub-path

Set `SCRIPT_PREFIX=/web` and have the proxy strip the prefix before
forwarding. Static URLs, media URLs, login redirects, the manifest, the PWA
scope and the service worker path are all derived from that one variable.

### Docker

```bash
docker compose up -d --build
```

The image runs Gunicorn as an unprivileged user and collects static files at
build time.

---

## Access URLs

Relative to the site root (prefixed with `SCRIPT_PREFIX` if set).

| URL | Description |
|---|---|
| `/` | Public home page |
| `/about/`, `/services/`, `/industries/`, `/our-work/`, `/contact/` | Public pages |
| `/accounts/login/`, `/accounts/register/` | Login and client registration |
| `/dashboard/` | Dashboard (admin or client, by role) |
| `/dashboard/projects/` | Project list |
| `/dashboard/analytics/` | Admin analytics |
| `/dashboard/machines/` | Machine inventory |
| `/dashboard/enquiries/` | Enquiry inbox |
| `/notifications/` | Notifications |
| `/admin/` | Django admin |
| `/api/projects/` | REST API |
| `/manifest.json` | Web app manifest |
| `/serviceworker.js` | Service worker |
| `/offline/` | Offline fallback page |

---

## Troubleshooting

**`Access denied for user … (using password: NO)`**
`DB_PASSWORD` is empty in `.env`, or `.env` has not been created.

**`Can't connect to MySQL server … getaddrinfo failed`**
`DB_HOST` cannot be resolved. Check the value; if it points at a managed
provider, confirm the service still exists.

**`Required environment variable SECRET_KEY is not set`**
Expected with `DEBUG=False`. Generate one as shown in [Local setup](#local-setup).

**`ALLOWED_HOSTS must list your real hostnames`**
`DEBUG=False` with a wildcard or empty `ALLOWED_HOSTS`. List the real
hostnames.

**Chrome does not offer to install the app**
Open **F12 → Application → Manifest** and read the errors. The usual causes
are: the page is not on HTTPS (and not `localhost`), the service worker did
not register, or `collectstatic` has not run so the icons 404.

**Static files missing after deploying**
Run `python manage.py collectstatic --noinput`. With `DEBUG=False` the hashed
manifest storage is used and requires it.

**`UnicodeEncodeError` from a management command on Windows**
Set `PYTHONIOENCODING=utf-8`, or use Windows Terminal. The bundled commands
print ASCII only.

---

## Security notes

Credentials were previously hardcoded in `config/settings.py`, which is in git
history: a MySQL password, a Gmail App Password and the Django `SECRET_KEY`.
They have been moved to environment variables, but **moving them does not undo
the exposure**. All three should be rotated at the provider:

- change the MySQL user's password
- revoke the Gmail App Password at
  [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
  and issue a new one
- generate a new `SECRET_KEY` (this invalidates existing sessions and password
  reset links, which is the intended effect)

---

## License

Built for **Shri Gouri Engineers**. All rights reserved.
