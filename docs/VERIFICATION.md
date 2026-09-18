# Verification record

## Automated

41 pytest cases passed against fresh, file-backed SQLite databases. Coverage includes:

- Income and expense create/read/update/delete and exact paise totals.
- Validation of amounts, dates, text lengths, category/type combinations and payment methods.
- Account isolation for listing, reading, editing, deleting, summaries and export.
- Signed-in access, CSRF rejection, password hashing, logout and login.
- Search, month/type/category filters, pagination and invalid filter handling.
- CSV formula escaping and export filter matching.
- Persistence across new app instances and database foreign-key enforcement.
- Local smart-entry drafts, ambiguous-input rejection, provider-error fallback and demo AI isolation.
- Health response, content-security policy and year/month boundaries.

The JavaScript file also passed `node --check`.

## Browser

The running local Gunicorn app was checked in a browser. Verified: demo login, actual database-derived totals and charts, draft creation, review dialog, saving a ₹123.45 record, editing it to ₹125.50, searching it, and opening/cancelling the delete confirmation. The demo test record is fictional. Permanent deletion is verified by the backend tests. Browser error/warning logs were empty at the interaction check.

The dashboard, charts and transaction dialog were also visually checked at a 390 × 844 mobile viewport. Mobile sign-out is available; wide transaction tables scroll within their own container. The normal desktop viewport was restored after checking.

## Limits

A live Gemini request was not made because no provider key was supplied. The default local parser is fully usable without one. Cloud hosting, a public URL, Docker image execution and GitHub Actions execution have not been verified. Their setup files are provided. Public hosting and a live Gemini request still need verification.
