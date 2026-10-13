# Plan: user journeys, tasks and status (Capstone checkpoint "Design")

All tasks are implemented. Automated tests were run on 2026-10-13 (all pass); manual checks are recorded in `VERIFICATION_LOG.md`.

## User journeys
**Individual** - registers as "Individual" -> logs in -> adds a subscription (category, amount, currency, cycle, renewal date, reminder days) -> sees it in "My Subscriptions" and the upcoming renewal on the dashboard -> receives a reminder notification -> records or imports a payment -> opens Reports to see the monthly estimate and totals per currency.

**Small business** - registers as "Business" (business name required) -> same flow, then reviews payments flagged "needs review" and uses reports to decide which subscriptions to pause or stop.

## Prioritized task list (each task has a completion condition)
| # | Task | Completion condition | Status |
|---|---|---|---|
| 1 | Project skeleton + design system (RTL, light/dark via session+cookie, CSS animations, emoji alerts, logo) | `manage.py test` passes; pages render in both modes and on mobile width | Done - automated tests pass |
| 2 | Models, constraints, migrations, admin; English ERD matching the models | Fresh DB builds from migrations; ERD lists exactly the implemented models/fields | Done - automated tests pass |
| 3 | Accounts: register (individual/business), login, logout | Business without a name is rejected on the server; passwords hashed by Django | Done - automated tests pass |
| 4 | My Subscriptions: CRUD, search, filter, order, pagination, archive rules, ownership checks | A user cannot open another user's record by URL (404/403) | Done - automated tests pass |
| 5 | Payments: CRUD, JSON import in a transaction, "needs review" flag | Invalid JSON saves nothing; similar payments flagged, never deleted | Done - automated tests pass |
| 6 | Notifications + `send_reminders` command + ReminderLog | No reminder for inactive subscriptions; no duplicate for the same (subscription, date, days) | Done - automated tests pass |
| 7 | Dashboard + Reports with `aggregate()` / `annotate()` | Totals correct with several related rows; currencies never mixed; empty data handled | Done - automated tests pass |
| 8 | Seed command, wireframes, custom 404/403/500 pages | Documented command creates fictional demo data and empty-state account | Done - automated tests pass |
| 9 | Automated tests, manual acceptance, fresh-setup check, final README | All 22 scenarios executed and recorded honestly | Done - automated tests pass |

## Blockers / open items
- Manual mobile-layout check and a fresh-checkout run on a second machine still have to be recorded in `VERIFICATION_LOG.md`.
- Market evidence (interviews / survey) not collected yet.
- Confirm scope with the instructor.