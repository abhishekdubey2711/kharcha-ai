import os
import secrets
import hmac
from datetime import timedelta
from pathlib import Path
from flask import Flask, session, request, jsonify, g
from werkzeug.exceptions import HTTPException
from .db import init_db, close_db, get_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    production = os.getenv('KHARCHA_ENV') == 'production'
    secret = os.getenv('SECRET_KEY')
    if production and not secret and not test_config:
        raise RuntimeError('Set a strong SECRET_KEY before production startup.')
    if not secret:
        secret_path = Path(app.instance_path) / 'secret.key'
        try:
            with secret_path.open('x') as f:
                f.write(secrets.token_hex(32))
            secret_path.chmod(0o600)
        except FileExistsError:
            pass
        secret = secret_path.read_text()
    app.config.from_mapping(
        SECRET_KEY=secret, DATABASE=os.getenv('DATABASE_PATH', str(Path(app.instance_path) / 'kharcha.sqlite')),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7), MAX_CONTENT_LENGTH=16 * 1024,
        GEMINI_API_KEY=os.getenv('GEMINI_API_KEY'), GEMINI_MODEL=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite'),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()

    @app.before_request
    def protect_request():
        session.setdefault('csrf_token', secrets.token_hex(32))
        g.user = None
        if session.get('user_id'):
            g.user = get_db().execute('SELECT id,name,email,is_demo FROM users WHERE id=?', (session['user_id'],)).fetchone()
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not hmac.compare_digest(token.encode(), session['csrf_token'].encode()):
                return jsonify(error='Session expired. Refresh the page and try again.'), 403

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers['Cache-Control'] = 'no-store'
        if production:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error=error.description), error.code
        return error

    from .auth import bp as auth_bp
    from .routes import bp as main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.cli.command('init-db')
    def init_command():
        """Create missing tables without deleting existing records."""
        init_db()
        print('Database ready.')

    @app.cli.command('clean-demos')
    def clean_demos():
        """Delete disposable demo accounts older than 7 days."""
        db = get_db()
        with db:
            result = db.execute("DELETE FROM users WHERE is_demo=1 AND created_at < datetime('now','-7 days')")
        print(f'Removed {result.rowcount} expired demo accounts.')

    return app
