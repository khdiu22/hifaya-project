
# Hifaya (حفاية)

A Django web application that helps **individuals and small businesses** keep all their subscriptions in one place, follow renewal dates, record payments, receive reminders and see simple reports. Capstone project.

> **Honest status.** The whole application is written, but it has **not been executed by its author's tooling** (Django was not available where the code was written). Every claim below is therefore "implemented in code" until you run the steps in section 14 and record real results in `docs/VERIFICATION_LOG.md`. Nothing is marked as passed before it has been run.

## Quick start on Windows (CMD) - all steps
```bat
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
set DEMO_PASSWORD=Demo-Pass-123!
python manage.py seed_demo --reset
python manage.py test
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/ . Next time only: `venv\Scripts\activate` then `python manage.py runserver`.
A full Arabic explanation of every file and folder is in `docs/PROJECT_GUIDE_AR.md`.

## Language, e-mail reminders and scheduler (latest changes)
- **Language (Arabic / English):** the 🌐 button works for visitors (login/register pages) and for signed-in users. For a signed-in user the choice is **saved in the account** (`Profile.preferred_language`), so it follows the user to any browser; the login page also applies it.
- **Reminders:** `notifications/services.py` writes the in-app notification **and** the e-mail in the language saved in each user's profile, even when the scheduler runs the command automatically. `ReminderLog` prevents duplicates.
- **Category names:** default categories are stored in Arabic in the database and translated only for display (`Category.display_name`); categories a user creates stay exactly as typed.
- **E-mail setup:** copy `.env.example` to `.env`, fill the `EMAIL_*` values (Gmail needs an *App password*), then test with `python manage.py send_test_email you@example.com`. Never upload `.env`.
- **Daily automatic run (Windows Task Scheduler):** run `run_reminders.bat` (it writes `logs\reminders.log`).
  ```bat
  schtasks /Create /SC DAILY /ST 09:00 /TN "Hifaya Daily Reminders" /TR "\"%CD%\run_reminders.bat\"" /F
  schtasks /Run /TN "Hifaya Daily Reminders"
  type logs\reminders.log
  schtasks /Query /TN "Hifaya Daily Reminders" /V /FO LIST
  ```
  A real success shows `Reminders created: ...` in the log and `Last Result: 0` in the query (a status of "Ready" alone proves nothing).

## Screenshots (to be taken by the author)
Take real screenshots of **your own running site** (not the reference images) and put them in `docs/screenshots/`, then link them here. The required shots and file names are listed in `docs/screenshots/README.md`.

## 1. Problem and target audience

**Problem.** People and small businesses pay for many recurring services. It is hard to follow renewal dates, costs and related payments, so renewals are forgotten and recurring expenses go unnoticed.

**Target audience**
1. Individuals with several subscriptions.
2. Small businesses that need to follow the subscriptions and recurring costs of their services.

## 2. Value and features

Value: all subscriptions in one place; upcoming renewals; estimated monthly cost per currency; payment records; reminders; reports that support spending decisions.

**Assumptions vs evidence.** The audience and value above are *assumptions*. No commercial demand and no money saved has been proven. Evidence collected so far: **none**. Planned: short survey/interviews with a few individuals and small-business owners; results will be added here.

**Possible adoption/revenue model (hypothesis, not validated).** Free plan for individuals (limited number of subscriptions); paid plan for small businesses (more subscriptions, team access, exports).

### The five main sections (and nothing else in the menu)
| Section | What it does |
|---|---|
| Dashboard | Live counts and totals, upcoming renewals, latest payments and notifications, empty state |
| My Subscriptions | Recurring and non-recurring subscriptions together: add, view, edit, archive, safe delete, search, filter, order, pagination |
| Payments | Manual entry, view, edit, archive/restore/delete rules, search/filter/order, JSON import, "needs review" flag for similar payments |
| Notifications | Reminder notifications, mark as read, filters, newest first, empty state |
| Reports | `aggregate()` / `annotate()` summaries, per-currency totals, filters |

Other features: registration (individual / business with a conditional business name checked on the server), login/logout, "remember me", light/dark mode (session + cookie), animated CSS toasts with emojis, service icons (see below), custom 404/403/500 pages, Django admin.

Out of scope by design: cancelling at the provider, bank integrations, JavaScript, AI inside the app.

## Languages (Arabic / English)
The whole interface is available in **Arabic (default, right-to-left)** and **English (left-to-right)**. Use the 🌐 button in the top bar (or the top corner of the login/register pages). The choice is stored by Django in the `django_language` cookie.

- Texts are written in Arabic in the code and translated through Django's standard gettext system: `{% trans %}` / `{% blocktrans %}` in templates and `gettext_lazy` (`_`) in Python.
- The English translations live in `locale/en/LC_MESSAGES/django.po` (compiled to `django.mo`, which is already included). If you edit the `.po` file, recompile with `python manage.py compilemessages` (needs GNU gettext) or any `.po` editor that writes `.mo`.
- Names typed by users (service names, notes) are never translated.

## 3. Technologies
Python, Django, Django Templates, HTML5, CSS3, SQLite (development), Django ORM, Django built-in authentication, Git and GitHub. **No JavaScript** anywhere: interactivity uses HTML forms (POST), server-side rendering and pure CSS (mobile menu and toast close button use the CSS checkbox technique). No React/Vue/Node.

## 4. Project structure
```
hifaya_project/
  manage.py, requirements.txt, .env.example, .gitignore
  config/            settings, root urls, wsgi/asgi
  core/              dashboard, theme switch, shared helpers, template tags, test factories
  accounts/          Profile model, register / login / logout
  subscriptions/     Category + Subscription, CRUD views, service icons, seed_demo command
  payments/          Payment model, CRUD, similar-payment rule, JSON importer
  notifications/     Notification + ReminderLog, reminder service, send_reminders command
  reports/           aggregate()/annotate() report view and filter form
  templates/         base.html, base_auth.html, partials/, one folder per app, 404/403/400/500
  static/css/        style.css (design system, light/dark, animations)
  static/img/        logo.png, favicon.png, services/ (optional official logos)
  docs/              ERD, wireframes, JSON import format, plan, verification log
  <app>/migrations/  schema migrations (+ default categories data migration)
  <app>/tests.py     automated tests
```

## 5. Requirements
- Python 3.10 or newer (the code was written against 3.12).
- Django `>=5.2,<5.3` (`requirements.txt`; the code uses `{% querystring %}` and `CheckConstraint(condition=...)`, both Django 5.1+). The exact version you install is printed by `python -m django --version`; write it here after your first run: **Django ____ / Python ____**.

## 6. Setup from a fresh checkout
```bash
git clone <your-repo-url>
cd hifaya_project
python -m venv venv
# Windows: venv\Scripts\activate        macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # optional fictional demo data (prints the demo password)
python manage.py runserver
```
Open http://127.0.0.1:8000/ . Create an admin user for `/admin/` with `python manage.py createsuperuser` (optional).

## 7. Environment variables (see `.env.example`)
| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Secret key (use a real random value outside development; never commit it) |
| `DJANGO_DEBUG` | `1` (default) in development, `0` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Real email through SMTP |
| `DEMO_PASSWORD` | Optional fixed password for `seed_demo` accounts |

## 8. Migrations
`python manage.py migrate` builds the schema from scratch and adds 8 default categories (data migration `subscriptions/0002_default_categories.py`). The migrations were written by hand: check them with `python manage.py makemigrations --check --dry-run` (expected: "No changes detected"). If it reports changes, run `makemigrations` and commit the generated files.

## 9. Demo (seed) data
`python manage.py seed_demo` (add `--reset` to recreate). Everything is fictional. Accounts (same password, printed once at the end, or set `DEMO_PASSWORD`):

| Account | Purpose |
|---|---|
| `demo.individual@example.com` | Individual: 13 subscriptions (active/paused/cancelled/archived, weekly..yearly, SAR/USD/EUR, soon/far/overdue renewals, a custom service with the globe icon), 13 payments (including two similar ones flagged for review, a failed one and one without a subscription), read and unread notifications |
| `demo.business@example.com` | Business account "شركة النخبة التجريبية" with 7 subscriptions, payments in SAR and USD |
| `demo.empty@example.com` | No data - shows the empty states |

Invalid-input cases are exercised by the automated tests and by `docs/sample_payments_invalid.json`. No real personal data or secrets are stored in the repository.

## 10. Running the server
`python manage.py runserver`

## 11. How to use the main functions
1. **Register** at `/accounts/register/` (choose Individual or Business; a business must give its name), then log in.
2. **Add a subscription**: My Subscriptions -> Add. Amount must not be negative; renewal date cannot be before the start date.
3. See it in **My Subscriptions** and its renewal on the **Dashboard**.
4. **Notifications -> "Check reminders now"** creates due reminders for your subscriptions (a subscription is "due" when today is within *reminder days* before its renewal date and it is active).
5. **Record a payment** (Payments -> Add, or from a subscription page) or **import JSON** (`docs/JSON_IMPORT.md`).
6. Open **Reports**; use the filters (period, status, category, subscription).
7. Switch **light/dark mode** from the top bar; the choice is saved in the session and a cookie.

Business rules in short: no negative amounts; payment currency must match its subscription's currency; a subscription with payments cannot be deleted (archive it); only archived payments can be deleted permanently; reminders are never sent for paused/cancelled/archived subscriptions and never repeated for the same (subscription, renewal date, days-before); "needs review" for payments means *similar* (same subscription, amount, currency, within 3 days) - not fraud; for subscriptions it means *active but the renewal date has passed*. Totals never add different currencies. Payments with status paid are the only ones counted in report totals.

### Service icons
The 30 named services (Netflix, Spotify, Shahid, YouTube Premium, Disney+, Amazon Prime Video, Anghami, Apple TV+, ChatGPT, Claude, Gemini, Perplexity, Microsoft Copilot, iCloud, Google One, Microsoft 365, Dropbox, Zoom, Notion, Google Workspace, Canva, Adobe Creative Cloud, Figma, GitHub, JetBrains, Amazon Prime, PlayStation Plus, Xbox Game Pass, Nintendo Switch Online, Duolingo Super) get a coloured badge icon; any other service gets the 🌐 globe icon in light purple. These are **generated badges, not official logos**; official logo files can be dropped into `static/img/services/` (see the README there).

## 12. Models and relationships
Full diagram: `docs/ERD.png` (and `docs/ERD.md`).

| Model | Purpose |
|---|---|
| `User` (Django) | Authentication, passwords hashed by Django |
| `Profile` | OneToOne with User: `account_type` (individual/business), `business_name`; DB CHECK requires a name for business |
| `Category` | Stored categories; unique `lower(name)` |
| `Subscription` | FK `user`, FK `category`; Decimal `amount`, currency, billing cycle, dates, status, `is_recurring`, `reminder_days_before`, notes; CHECKs: amount >= 0 and renewal >= start |
| `Payment` | FK `user`, optional FK `subscription`; amount/currency/date/method/reference/status, `review_required`, `review_reason`, `is_archived`; CHECK amount >= 0 |
| `Notification` | FK `user`, optional FK `subscription`, title, message, `is_read` |
| `ReminderLog` | FK `subscription`; UNIQUE (subscription, renewal_date, days_before) prevents duplicate reminders |

`on_delete`: `Payment.subscription` and `Subscription.category` use `RESTRICT` (financial data is protected; archive instead); notifications and reminder logs cascade with their subscription.

## 13. Where the required ORM features are used (real application features)
| Requirement | Location |
|---|---|
| CRUD | `subscriptions/views.py` (create/update/detail/archive/delete), `payments/views.py` (create/update/archive/restore/delete/import), `notifications/views.py` (mark read) |
| Filtering and search | `subscription_list`, `payment_list`, `notification_list` (+ filter forms) |
| Ordering | `ORDERING_MAP` in the subscription and payment views; `Meta.ordering` on models; notifications newest first |
| Relationship queries | `subscription_detail` (`sub.payments`, notifications), `reports/views.py` (`payments.filter(subscription__category=...)`, `Category` -> `subscriptions`), `select_related` in lists and dashboard |
| `aggregate()` | `core/views.dashboard` (conditional counts), `reports/views.report` (paid totals per currency in one query, renewals in a period, review count), `subscription_detail` (total paid) |
| `annotate()` | `reports/views.report` (subscriptions per category via `Category.annotate(Count)`, total paid per subscription via `Subscription.annotate(Sum)`, counts per status), `subscription_list` (`payments_count`), `subscriptions/services.monthly_cost_by_currency` |
| `Q` / `F` | `Q`: conditional aggregates in reports and dashboard, payment form queryset; `F`: the `next_renewal_date >= start_date` constraint |
| `select_related` / `prefetch_related` | `select_related` used in lists; `prefetch_related` is not used because it is not needed |
| Transactions | `payments/importer.import_rows` (all-or-nothing JSON import), `accounts/forms.RegisterForm.save`, reminder creation |

Correctness with several related rows: report sums use filtered `Sum`/`Count` over a single join, so extra payments never inflate subscription or category counts (tests in `reports/tests.py`).

**Request flow example (for the oral discussion):** `GET /subscriptions/?q=net` -> `config/urls.py` includes `subscriptions/urls.py` (`name="list"`) -> `subscription_list` view validates `SubscriptionFilterForm`, builds the queryset `Subscription.objects.filter(user=request.user)...` (ORM -> SQL on SQLite) -> paginates -> renders `templates/subscriptions/list.html` which extends `base.html`.

## 14. Running the tests
```bash
python manage.py test
```
About 130 automated tests cover registration rules, authentication, validation, ownership, CRUD, filters/ordering/pagination, payments, the JSON importer (including all-or-nothing behaviour), similar-payment flagging, reminders and duplicates, report totals with known data, currency separation, theme/session/cookie behaviour, and that models and migrations are in sync. Manual acceptance checks and their results go in `docs/VERIFICATION_LOG.md` (all rows are *Pending* until you run them).

## 15. Reminders and email
- Rule: an **active** subscription gets a reminder when `renewal date - today <= reminder_days_before` (and the renewal date is today or later). `ReminderLog` + a unique constraint prevent repeats.
- In-app: **Notifications -> Check reminders now** (own subscriptions only) or the command below.
- Command: `python manage.py send_reminders` (optional `--today YYYY-MM-DD` to simulate a date in a demo).
- **Daily sending is not automatic.** Schedule the command yourself, for example Linux/macOS cron `0 8 * * * cd /path/to/hifaya_project && venv/bin/python manage.py send_reminders`, or Windows Task Scheduler running `venv\Scripts\python.exe manage.py send_reminders` daily.
- Email: in development messages are printed in the terminal (console backend). Real email requires SMTP environment variables (section 7), for example `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`.

## 16. Demo information
Reproduce the demo: follow section 6, then log in with the demo accounts. Suggested order (from the brief): problem/users/evidence -> register or log in as an individual -> add a subscription -> see it in My Subscriptions -> see the renewal on the dashboard -> show a due reminder (real, from seed dates; say clearly that scheduling is manual) -> record a payment or import `docs/sample_payments.json` -> open Reports -> point to `aggregate()` (`reports/views.py`, paid totals) and `annotate()` (category counts) -> show a failed validation (negative amount) -> explain one relationship, one constraint and one technical decision (e.g. `RESTRICT` to protect financial data) -> market potential, limitations and next improvement. **Deployment link:** none (not deployed).

## 17. Capstone Guide checklist
| Guide requirement | Status |
|---|---|
| Clear problem and audience | Written (section 1); evidence still to be collected |
| Core workflow works end to end with persisted data | Implemented; **pending your test run** |
| Django + relational DB + ORM | Implemented |
| Models, relationships, constraints | Implemented (section 12) |
| ERD matches models | `docs/ERD.*` written from the models; test checks migrations are in sync |
| Migrations work from a fresh setup | Written by hand; **pending** (`migrate` + `makemigrations --check`) |
| CRUD, search/filter/order, pagination | Implemented; pending test run |
| Relationship queries, `aggregate()`, `annotate()` in real features | Implemented (section 13) |
| Correct totals with several related rows | Tests written; **pending** |
| Validation and error messages; empty states; missing records | Implemented (server-side validation, messages, 404/403/500 pages) |
| Server-side permissions | Implemented (every query is scoped to `request.user`; others get 404) |
| Responsive, accessible interface | Implemented (labels, ARIA, alt text, responsive CSS); **mobile check pending** |
| Sample data | `seed_demo` |
| Manual verification record | `docs/VERIFICATION_LOG.md` (all pending) |
| Automated tests | Written; **not yet run** |
| README allows a fresh setup | Written; **fresh-setup check pending** |
| No secrets / private data in the repository | `.gitignore`, `.env.example`, seed password generated at run time |
| Demo matches the real version | Section 16 |

## 18. Known limitations and future improvements
- Nothing has been executed yet by the author's tooling; results of your first run decide what is truly working (see the verification log).
- Hand-written migrations may need regeneration (section 8).
- Service icons are generated badges (no official logos); the Tajawal font needs internet (falls back to system fonts).
- Reminders are not scheduled automatically; there is no currency conversion (totals are per currency).
- Future: exchange rates with a documented source, CSV export, team accounts for businesses, deployment, password reset by email.

## 19. External help and sources
AI assistance (Claude by Anthropic) was used to help generate code, designs and documentation in this project. The author must review, adapt and verify everything and be able to explain it. Fonts: Tajawal (Google Fonts, open license). Logo: image supplied by the author. Add any other source or help you use here.

## 20. Git workflow
Commit after each meaningful step with a clear message (for example `Add Subscription model and migrations`, `Add payments JSON import`). Never commit `.env`, `db.sqlite3` or `venv/` (already ignored). Give the instructor access before submission.
=======
# Khadijah-Capstone-Project

