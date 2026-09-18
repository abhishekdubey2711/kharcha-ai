import secrets
import re
import time
import sqlite3
from functools import wraps
from flask import Blueprint, g, request, session, redirect, url_for, render_template, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db

bp = Blueprint('auth', __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith('/api/'):
                return jsonify(error='Please sign in.'), 401
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def rate_limit(bucket, limit, seconds):
    """SQLite-backed limit works across Gunicorn workers. Call before expensive work."""
    now = int(time.time())
    db = get_db()
    with db:
        db.execute('DELETE FROM rate_events WHERE occurred_at < ?', (now - 3600,))
        count = db.execute('SELECT COUNT(*) FROM rate_events WHERE bucket=? AND occurred_at>?',
                           (bucket, now - seconds)).fetchone()[0]
        if count >= limit:
            return False
        db.execute('INSERT INTO rate_events(bucket,occurred_at) VALUES (?,?)', (bucket, now))
    return True


def start_session(user_id):
    session.clear()
    session['user_id'] = user_id
    session['csrf_token'] = secrets.token_hex(32)
    session.permanent = True


@bp.route('/register', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    registering = request.path == '/register'
    error = None
    if request.method == 'POST':
        if not rate_limit(f'auth:{request.remote_addr}', 20, 900):
            return render_template('auth.html', registering=registering, error='Too many attempts. Try again in 15 minutes.'), 429
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 254:
            error = 'Enter a valid email address.'
        elif not 8 <= len(password) <= 128:
            error = 'Use a password between 8 and 128 characters.'
        elif registering and not 1 <= len(name) <= 60:
            error = 'Enter a name between 1 and 60 characters.'
        else:
            db = get_db()
            if registering:
                try:
                    with db:
                        cursor = db.execute('INSERT INTO users(name,email,password_hash) VALUES (?,?,?)',
                                            (name, email, generate_password_hash(password)))
                    start_session(cursor.lastrowid)
                    return redirect(url_for('main.dashboard'))
                except sqlite3.IntegrityError:
                    error = 'This email is already registered. Sign in instead.'
            else:
                user = db.execute('SELECT * FROM users WHERE email=? AND is_demo=0', (email,)).fetchone()
                if user and check_password_hash(user['password_hash'], password):
                    start_session(user['id'])
                    return redirect(url_for('main.dashboard'))
                error = 'Email or password is incorrect.'
    return render_template('auth.html', registering=registering, error=error), 400 if error else 200


@bp.post('/demo')
def demo():
    if not rate_limit(f'demo:{request.remote_addr}', 10, 3600):
        return render_template('auth.html', registering=False, error='Demo limit reached. Create an account to continue.'), 429
    from .seed import seed_demo
    db = get_db()
    with db:
        cursor = db.execute('INSERT INTO users(name,email,password_hash,is_demo) VALUES (?,?,?,1)',
                            ('Abhishek', f'{secrets.token_hex(16)}@demo.invalid', '!disabled'))
        seed_demo(db, cursor.lastrowid)
    start_session(cursor.lastrowid)
    return redirect(url_for('main.dashboard'))


@bp.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
