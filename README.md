# SL Property Hub

A Django-based nationwide property listing and company advertising platform for Sierra Leone. Property sales/rentals and advertiser payments happen offline; the application records payment submissions and requires an administrator to verify them before activating paid access.

## Included

- Custom user accounts and roles: property owner, property agent, company advertiser, platform administrator.
- Trial subscription automatically assigned to new owner/agent accounts: 10 listing slots for 14 days.
- Separate subscription catalog for property/land listings and company advertising.
- Admin-editable prices, durations, listing limits, plan descriptions, and activation state.
- Offline payment submission (Orange Money, AfriMoney, bank transfer, other offline payment), transaction reference/notes and optional receipt upload. No payment is collected on the website.
- Admin verification action activates the subscription; pending payments never unlock paid features.
- Property listing quota enforcement, immediate publication for an eligible owner/agent, photo uploads, photo deletion, and listing edits.
- Countrywide location field with Sierra Leone regions/district/city/neighborhood text support.
- Property search and filters, contact/inquiry forms, email notification support, phone/WhatsApp fields, view and inquiry counters.
- Company ad plans separate from property listing plans, advertiser ad creation, timed campaigns, click tracking and admin management.
- Django admin, PostgreSQL configuration, SQLite local development, WhiteNoise, Gunicorn and Docker Compose deployment files.

## Important business logic

1. Owners/agents register with role `owner` or `agent`; a 14-day trial plan with 10 listing slots is assigned automatically.
2. While a listing subscription is active and has quota, an owner/agent can create or edit listings. A new listing is published immediately, without moderation. Listings are hidden when their subscription expires.
3. Plans are configured at `/admin/` under **Subscriptions → Plans**. A property plan's `listing_limit` is the number of listings included; `price_sle` is the amount charged in SLE. Example: set price to 500 and listing limit to 10.
4. The user submits an offline payment record from the Plans page. It remains pending until staff verifies it under **Subscriptions → Payments**. Use the admin action **Verify selected offline payments and activate plans**. Staff can also mark a payment verified in its detail form; that path activates the plan too.
5. Company advertisers use plans with kind **Company advertising**. They must have a verified, active ad subscription before creating campaigns. Campaign end date follows the subscription end date.
6. Trial users can create up to 10 listings within the trial period. When the trial ends, new listing creation is blocked and listings are hidden until an active plan is obtained. The trial plan is editable in admin.

## Local setup (Windows PowerShell)

Install Python 3.12+ and Node.js 20+ (Node is only needed to rebuild Tailwind CSS).

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

For local development, edit `.env`: set `DJANGO_DEBUG=True`, use a development-only random secret, and keep `DATABASE_URL` unset to use SQLite. Then run:

```powershell
python manage.py makemigrations users properties subscriptions advertisements inquiries dashboard
python manage.py migrate
python manage.py seed_plans
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`; admin is at `http://127.0.0.1:8000/admin/`.

To rebuild CSS:

```powershell
npm install
npm run build:css
```

## Docker deployment

1. Copy `.env.example` to `.env`.
2. Set a long random `DJANGO_SECRET_KEY`, a unique strong `POSTGRES_PASSWORD`, real `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` values. Configure real SMTP values if email notifications are needed.
3. Deploy behind HTTPS at your hosting provider or reverse proxy. Do not expose the PostgreSQL port publicly.
4. Run:

```bash
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
```

The container entrypoint bootstraps initial migrations, applies migrations, seeds the trial plan, collects static assets and starts Gunicorn. For a long-lived production team workflow, generate and commit Django migrations as part of the release process before subsequent schema changes, rather than relying on startup migration generation.

## Production checklist

- Use HTTPS and a production-grade secret key; `DEBUG=False` is enforced by Docker Compose.
- Configure domain, CSRF trusted origins, SMTP and database credentials in `.env`.
- Back up PostgreSQL and uploaded media separately; persistent Docker volumes are configured for both.
- Restrict admin access, enable MFA at the identity/provider layer if available, and review staff permissions regularly.
- Set maximum upload sizes at the reverse proxy too. Property photo uploads are limited to 12 per save and 8 MB each; file content is validated as JPG/PNG/WebP.
- Configure a scheduled job for `python manage.py expire_subscriptions` to update expired status records. Public listing queries also exclude expired listing dates even if the scheduled job has not run.
- Test restore procedures, email delivery, error monitoring, and performance under expected traffic before launch.

## Payment and compliance boundary

This application does not process Orange Money, AfriMoney, bank or card transactions and must never request a wallet PIN, password or OTP. The payer transfers money using payment details communicated through the platform's official channel, submits a reference and optional proof, and staff verify the transaction independently. Actual merchant API integrations, automated reconciliation, SMS/WhatsApp provider integrations, cloud object storage, CDN, and advanced bot protection require provider credentials and deployment-specific configuration.

## Known deployment note

The source package is syntax-checked, but this build environment had no network access to install Django dependencies, so full `manage.py check`, migration execution, browser tests and end-to-end PostgreSQL tests could not be run here. Run the setup steps above in an environment with package access before accepting real users or payments.
