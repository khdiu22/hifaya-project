# Verification log

**Rule:** A row is changed to Passed / Failed only after the scenario was really executed.

**Run on 2026-10-13:**
- `python manage.py check` -> No issues found.
- `python manage.py makemigrations --check --dry-run` -> "No changes detected".
- `python manage.py migrate` on an empty database -> OK.
- `python manage.py seed_demo --reset` -> OK.
- `python manage.py test` -> 155 tests, all application tests passed successfully.
- **Environment:** Python 3.12, Django 5.2.18.
- **Manual & Language Checks:** Executed and verified.

---

## A. Scenarios required by the project brief

| # | Scenario | Expected result | Evidence (automated test / manual) | Actual result | Status |
|---|---|---|---|---|---|
| 1 | Register as an individual | User + Profile(individual) saved; redirected to login | `accounts.tests.RegisterTests.test_register_individual` | Automated test passed (2026-10-13) | Passed |
| 2 | Register as a business with a name | Profile(business) with business name saved | `RegisterTests.test_register_business_with_name` | Automated test passed (2026-10-13) | Passed |
| 3 | Reject business without a name | Form error on business name; no user created | `RegisterTests.test_business_without_name_is_rejected`, `test_business_with_blank_spaces_name_is_rejected`, `test_database_enforces_business_name` | Automated tests passed (2026-10-13) | Passed |
| 4 | Login and logout | Login -> dashboard; logout (POST) ends the session | `accounts.tests.LoginLogoutTests` | Automated test passed (2026-10-13) | Passed |
| 5 | Add a subscription and save it | Row exists in the database for this user | `subscriptions.tests.SubscriptionCrudTests.test_create_saves_to_database` | Automated test passed (2026-10-13) | Passed |
| 6 | Edit a subscription | Change persisted | `SubscriptionCrudTests.test_update_persists_changes` | Automated test passed (2026-10-13) | Passed |
| 7 | Search, filter, order | Correct subset and order | `FilterOrderPaginateTests`, `payments.tests.PaymentFilterTests` | Automated tests passed (2026-10-13) | Passed |
| 8 | Empty subscriptions list | Friendly empty state | `FilterOrderPaginateTests.test_empty_list_message`, `core.tests.DashboardTests.test_empty_state_for_new_user` | Automated tests passed (2026-10-13) | Passed |
| 9 | Reject negative amount | Error shown; nothing saved (form and database constraint) | `SubscriptionCrudTests.test_negative_amount_rejected`, `test_database_rejects_negative_amount`, payments equivalent | Automated tests passed (2026-10-13) | Passed |
| 10 | Reject missing required fields | Errors per field; nothing saved | `SubscriptionCrudTests.test_missing_required_fields_rejected` | Automated test passed (2026-10-13) | Passed |
| 11 | A user cannot reach another user's data (also by typing the URL) | 404, data unchanged | `OwnershipTests`, `payments.tests.PaymentCrudTests.test_other_user_gets_404`, `notifications.tests.NotificationViewTests.test_cannot_mark_other_users_notification` | Automated tests passed (2026-10-13) | Passed |
| 12 | Record a payment linked to a valid subscription | Payment saved with that subscription | `PaymentCrudTests.test_create_linked_to_own_subscription` | Automated test passed (2026-10-13) | Passed |
| 13 | Reject a payment linked to someone else's subscription | Form error; nothing saved | `PaymentCrudTests.test_cannot_link_to_someone_elses_subscription` | Automated test passed (2026-10-13) | Passed |
| 14 | JSON import: valid file accepted, invalid rejected | Valid -> saved; any invalid row -> nothing saved + clear errors | `payments.tests.JsonImportTests`; manual with `docs/sample_payments*.json` | Automated & manual tests passed (2026-10-13) | Passed |
| 15 | Similar payments are shown for review, never deleted automatically | Both flagged, both still exist | `payments.tests.SimilarPaymentTests` | Automated test passed (2026-10-13) | Passed |
| 16 | Reminder timing and no duplicates | One reminder per (subscription, renewal date, days); none for inactive | `notifications.tests.ReminderLogicTests` | Automated test passed (2026-10-13) | Passed |
| 17 | Report totals with known data | SAR 160.00 (4 payments), USD 50.00 (1) | `reports.tests.ReportsTests.test_currency_totals_are_separate_and_correct` | Automated test passed (2026-10-13) | Passed |
| 18 | `aggregate()` and `annotate()` with several related rows | No inflated sums or counts | `ReportsTests.test_per_subscription_totals_not_inflated`, `test_category_counts_not_inflated_by_payments` | Automated tests passed (2026-10-13) | Passed |
| 19 | Currencies are never mixed | One total per currency | `ReportsTests`, `subscriptions.tests.MonthlyCostTests`, `core.tests.DashboardTests.test_monthly_estimate_uses_active_subscriptions_only` | Automated tests passed (2026-10-13) | Passed |
| 20 | Delete / archive records that have dependencies | Subscription with payments cannot be deleted but can be archived; payments archive/restore/delete rules | `DeleteArchiveTests`, `PaymentCrudTests.test_archive_restoreش