"""One SQLite connection per request; values always use SQL parameters."""
import sqlite3
import time
from pathlib import Path
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    # First-boot workers may race while changing the journal mode.
    for attempt in range(20):
        try:
            db.execute('PRAGMA journal_mode = WAL')
            break
        except sqlite3.OperationalError as error:
            if 'locked' not in str(error) or attempt == 19:
                raise
            time.sleep(0.05)
    db.executescript(Path(__file__).with_name('schema.sql').read_text())


def as_transaction(row):
    result = dict(row)
    # Keep the API amount decimal as a string. Never round-trip money through floats.
    result['amount'] = f"{result['amount_paise'] // 100}.{result['amount_paise'] % 100:02d}"
    return result
