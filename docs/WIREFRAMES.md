# Wireframes (simplified, RTL: the sidebar sits on the right)

Legend: `[ ]` button/input, `( )` radio, `{...}` data from the database.

## 1) Registration (`/accounts/register/`)
```
+---------------------------------------------+
|                      [🌙 Dark mode]          |
|            (logo) Hifaya                     |
|  Create account                              |
|  Name *            [__________]              |
|  Email *           [__________]              |
|  Password *        [__________]              |
|  Confirm password *[__________]              |
|  Account type *    (•) Individual ( ) Business|
|  Business name     [__________]  required for Business (checked on the server)
|  [ Create account ]    Already registered? Login
+---------------------------------------------+
```

## 2) Dashboard (`/`)
```
+----------+--------------------------------------------------+
| Sidebar  | Dashboard                    👤 name [Theme][Logout]
| Dashboard|--------------------------------------------------|
| My subs  | [Active {n}] [Monthly cost {per currency}]        |
| Payments | [Renewing in 7 days {n}] [Need review {n}]        |
| Notifs(n)|--------------------------------------------------|
| Reports  | Upcoming renewals {table} | Latest payments {table}|
|          | Latest notifications {list}                       |
+----------+--------------------------------------------------+
Empty account: "You have not added any subscription yet" + [Add subscription]
```

## 3) My Subscriptions (`/subscriptions/`)
```
[ + Add subscription ]
Filters: search [____] status [v] category [v] cycle [v] order [v] [x] needs review  [Search][Clear]
+----------------------------------------------------------------------------+
| icon Service | Category | Amount | Cycle | Start | Next renewal | Status | ...| [View][Edit]
| {rows, 10 per page}                                                         |
+----------------------------------------------------------------------------+
< Previous   page 1 of 3   Next >
No matches: "No subscriptions match the filters" + [Clear]
```
Subscription details: data + related payments + notifications; buttons Edit / Record payment / Archive / Delete (confirmation page).

## 4) Add / edit subscription (`/subscriptions/add/`)
```
Service name * [____] (suggestions)   Category * [v]
Amount * [____]  Currency [v]  Billing cycle [v]
Start date * [date]  Next renewal * [date]  Status [v]
Recurring? (•) Yes ( ) No   Remind me [3] days before   Notes [______]
[ Save ] [ Cancel ]            Errors appear under each field (server-side)
```

## 5) Payments (`/payments/`)
```
[ + Record payment ] [ Import JSON ]    "🔎 n payments need review" (similar payments, not fraud)
Filters: subscription [v] status [v] from [date] to [date] show [v] order [v] [x] needs review
+------------------------------------------------------------------------+
| #id | Subscription | Amount | Currency | Date | Method/Ref | Status | Review | [View]
+------------------------------------------------------------------------+
```
Payment details: Edit / Archive (then Restore / permanent Delete with confirmation) / "I reviewed it".

## 6) Notifications (`/notifications/`)
```
[ Check reminders now ] [ Mark all read ]   filters: state [v] from [date] to [date]
 ● 🔔 Reminder: Netflix — "⏳ 3 days left on Netflix, renews soon, hurry and edit it!"  [Mark read]
 ○ ...                                       (newest first, unread highlighted)
```

## 7) Reports (`/reports/`)
```
Filters: from [date] to [date] status [v] category [v] subscription [v] [Show]
[Estimated monthly cost per currency] [Paid totals per currency in period + renewals count]
[Subscriptions by status] [Subscriptions by category]
[Total paid per subscription]  [Needs review: overdue subscriptions + flagged payments]
No data: "Not enough data yet" + [Add subscription]
```
