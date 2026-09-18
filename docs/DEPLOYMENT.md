# Run, deploy and preserve the data

## Delivered status

The application has been run locally with **Gunicorn and two worker processes**. This package also includes Docker Compose and a Render Blueprint. No public cloud service has been provisioned. Docker and Render deployment are configuration deliverables, not claimed live deployments. An account on the chosen Python host is needed for a public URL.

## Local production-server check

After installing the requirements, on macOS/Linux:

```bash
gunicorn --bind 127.0.0.1:5057 --workers 2 --preload --access-logfile - wsgi:app
```

Open `http://127.0.0.1:5057/health`; expect `{"status":"ok"}`. The development Flask server is only for local work. Gunicorn is the WSGI server used for deployment, following [Flask's deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/).

## Docker locally

1. Copy `.env.example` to `.env`.
2. Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"` and set `SECRET_KEY` in `.env`.
3. Run `docker compose up --build -d`.
4. Open `http://localhost:8000`.

The named volume `kharcha-data` stores the SQLite database independently of containers. Ordinary `docker compose down` preserves it. Removing the volume deletes the ledger. The Compose setup is loopback-only and intentionally uses HTTP-compatible cookies for a local demonstration. Do not treat it as a complete public HTTPS deployment.

## Public Python hosting: Render example

The included `render.yaml` describes a native Python web service with a persistent disk. It uses a paid service/disk configuration; check the hosting dashboard's cost before provisioning. The blueprint does not deploy itself when you unzip this project.

1. Upload the project source to your GitHub repository, excluding `.env`, `instance/`, caches and private records.
2. In Render, create a Blueprint from that repository, or create a Python web service manually.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --preload wsgi:app`.
5. Attach a persistent disk at `/var/data`. Set `DATABASE_PATH=/var/data/kharcha.sqlite`.
6. Set `KHARCHA_ENV=production` and a persistent random `SECRET_KEY`. The blueprint generates the secret.
7. Set the health-check path to `/health`. Use the HTTPS URL supplied by the host.
8. Optional: set `GEMINI_API_KEY` and `GEMINI_MODEL` through the host's secret settings.

Render documents its [Flask deployment steps](https://render.com/docs/deploy-flask) and [Blueprint schema](https://render.com/docs/blueprint-spec). Its default filesystem is ephemeral; a [persistent disk](https://render.com/docs/disks) preserves files only under the mount path and is attached to a single service instance. Keep this SQLite app on one instance. Use PostgreSQL before scaling across instances.

The app initializes schema at runtime so it can access the mounted disk. Production cookies require HTTPS. `SECRET_KEY` must stay consistent across restarts; changing it logs out sessions. The application deliberately does not trust arbitrary forwarded proxy headers. Authentication rate limits are keyed by the server-visible remote address, so behind a proxy they may be shared; configure trusted proxy handling for your actual host if needed.

## Verify a public deployment

- Confirm `/health` returns 200.
- Create a personal account and save a test record.
- Restart/redeploy the service, sign in, and verify that record remains.
- Verify edit, delete, month filters and CSV export.
- Open a separate account and confirm it cannot see the first account's data.
- Confirm Secure and HttpOnly session-cookie flags under HTTPS.
- If enabling Gemini, test with a harmless sentence and confirm the returned `source` is `gemini`; a local fallback is not evidence of a live AI call.
- Record the actual public URL and date only after these checks pass.

## Backups and restore

Use SQLite's backup API for a consistent snapshot while the app is running. Do not copy only the main file during active WAL writes.

```python
import sqlite3
from pathlib import Path

source_path = Path('instance/kharcha.sqlite').resolve()
backup_path = Path('kharcha-backup.sqlite').resolve()
if backup_path.exists():
    raise FileExistsError('Choose a new backup filename.')
with sqlite3.connect(f'{source_path.as_uri()}?mode=ro', uri=True) as source:
    with sqlite3.connect(backup_path) as destination:
        source.backup(destination)
```

Run this from the project root; for a hosted instance, use its configured database path and store backups outside the repository. Protect backups as personal data. To restore, stop the app, keep a copy of the current database and its WAL/SHM companions, restore the backup into a clean database path, set `DATABASE_PATH` to that file and restart. Verify before removing old files.

## Maintenance

`flask --app wsgi clean-demos` removes fictional demo accounts older than seven days and their records. It does not delete real accounts. Schedule it yourself if the service is publicly accessible; no external scheduled task has been created. Version 1 is the initial schema. Future changes need reviewed migrations and a backup before deployment.
