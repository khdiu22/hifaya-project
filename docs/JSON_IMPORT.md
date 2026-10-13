# JSON payment import format (Hifaya schema)

This is **Hifaya's own documented format**. It is not a format produced automatically by banks.


{
  "payments": [
    {
      "subscription_id": 3,
      "amount": "45.00",
      "currency": "SAR",
      "payment_date": "2026-10-01",
      "payment_method": "Card",
      "reference": "INV-1001",
      "status": "paid",
      "notes": ""
    }
  ]
}


| Field | Required | Rule |
|---|---|---|
| `amount` | yes | Number or string, not negative, at most 2 decimals, below 100,000,000 |
| `currency` | yes | One of `SAR`, `USD`, `EUR`, `GBP`, `AED` |
| `payment_date` | yes | ISO date `YYYY-MM-DD` |
| `subscription_id` | no | Integer id of **your own** subscription (shown on its details page) or `null`; the payment currency must equal the subscription currency |
| `status` | no | `paid` (default), `pending`, `failed`, `refunded` |
| `payment_method` | no | Text up to 50 characters |
| `reference` | no | Text up to 100 characters |
| `notes` | no | Text up to 1000 characters |

Limits: file up to 1 MB, up to 500 payments.

Behaviour
- The whole file is validated first; if **any** row is invalid, **nothing** is saved and the page lists the problems.
- Valid files are saved inside one database transaction.
- Imported payments that look similar to existing ones (same subscription, amount and currency within 3 days) are flagged "needs review". Nothing is deleted automatically and a flag is **not** an accusation of duplication or fraud.

Sample files: `sample_payments.json` (valid, no subscription ids) and `sample_payments_invalid.json` (for demonstrating the error handling).
