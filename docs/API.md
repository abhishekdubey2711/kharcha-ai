# API reference

All `/api/*` endpoints require a signed-in session. GET `/health` is public. Requests that change state also require `X-CSRF-Token`, taken from the page's `meta[name=csrf-token]`. The session cookie and token must belong to the same session. Sign-in rotates the token. JSON errors have the form `{"error":"message"}`.

| Method | Endpoint | Result |
|---|---|---|
| GET | `/api/categories` | Category IDs, names, and transaction types |
| GET | `/api/transactions` | Paginated records for the current user |
| POST | `/api/transactions` | Create a record; 201 |
| GET | `/api/transactions/<id>` | Read one owned record |
| PUT | `/api/transactions/<id>` | Replace all editable fields |
| DELETE | `/api/transactions/<id>` | Delete owned record; 204 |
| GET | `/api/summary?month=2026-09` | Monthly totals, categories, six-month trend, current balance |
| GET | `/api/export` | CSV download, matching filters; all matching rows |
| POST | `/api/parse` | Produce a draft; never saves it |

## Transaction body

```json
{
  "kind": "expense",
  "amount": "180.25",
  "category_id": 1,
  "description": "Coffee with friends",
  "date": "2026-09-15",
  "payment_method": "UPI",
  "notes": "After class"
}
```

`amount` is an INR decimal string, with up to two decimal places. It is stored as integer paise. Responses include both `amount` and `amount_paise`. All summary amounts are integer paise. Allowed payment methods: `UPI`, `Cash`, `Card`, `Bank transfer`. Dates must be valid ISO calendar dates. Categories must match income or expense. PUT is a full replacement, not a partial update.

## List/export filters

- `month=YYYY-MM`: records in that calendar month; omitted means all dates.
- `kind=income` or `kind=expense`.
- `category_id=1`.
- `q=coffee`: case-insensitive literal substring search of description and notes.
- List only: `page=1`, `per_page=10` (maximum 100).

Records sort by date descending, then ID descending. The dashboard applies its selected month to the table, charts and export. Current balance is the exception: all income minus expenses through today. Monthly totals include any future-dated records in that month; no automatic bank synchronization occurs.

## Smart entry

```json
{"text":"Spent ₹180 on coffee yesterday"}
```

Returns `draft`, `source` (`local` or `gemini`), and `notice`. Gemini requires a server-side key and is disabled in demo workspaces. If unavailable or invalid, it falls back to the local parser. The local parser only supports simple single-amount inputs and today/yesterday/ISO dates. Review defaults before saving.

## Status codes

200 success; 201 created; 204 deleted; 400 invalid fields; 401 unsigned; 403 missing/incorrect CSRF; 404 absent or another user's record; 413 body over 16 KB; 415 incorrect request content type; 429 too many attempts.
