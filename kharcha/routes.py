import csv
import io
import re
from datetime import date
from flask import Blueprint, render_template, jsonify, request, g, Response, current_app
from .auth import login_required, rate_limit
from .db import get_db, as_transaction
from .validation import validate_transaction

bp = Blueprint('main', __name__)
SELECT = 'SELECT t.*, c.name AS category FROM transactions t JOIN categories c ON c.id=t.category_id'


def month_range(month):
    if not re.fullmatch(r'\d{4}-\d{2}', month):
        raise ValueError('Use a month in YYYY-MM format.')
    first = date.fromisoformat(month + '-01')
    if first.year < 1900 or first.year > 9998:
        raise ValueError('Year must be between 1900 and 9998.')
    following = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
    return first.isoformat(), following.isoformat()


def filters():
    clauses, args = ['t.user_id=?'], [g.user['id']]
    month = request.args.get('month', '')
    if month:
        start, end = month_range(month)
        clauses.append('t.date>=? AND t.date<?')
        args.extend([start, end])
    kind = request.args.get('kind', '')
    if kind:
        if kind not in ('income', 'expense'):
            raise ValueError('Invalid transaction type.')
        clauses.append('t.kind=?')
        args.append(kind)
    category = request.args.get('category_id', '')
    if category:
        if not category.isdigit():
            raise ValueError('Invalid category.')
        clauses.append('t.category_id=?')
        args.append(int(category))
    query = request.args.get('q', '').strip()
    if len(query) > 120:
        raise ValueError('Search must be at most 120 characters.')
    if query:
        clauses.append("(instr(lower(t.description),lower(?)) > 0 OR instr(lower(t.notes),lower(?)) > 0)")
        args.extend([query, query])
    return ' WHERE ' + ' AND '.join(clauses), args


@bp.get('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user=g.user, today=date.today().isoformat(),
                           ai_enabled=bool(current_app.config['GEMINI_API_KEY']))


@bp.get('/health')
def health():
    get_db().execute('SELECT 1').fetchone()
    return jsonify(status='ok')


@bp.get('/api/categories')
@login_required
def categories():
    return jsonify(categories=[dict(r) for r in get_db().execute('SELECT * FROM categories ORDER BY id')])


@bp.route('/api/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    db = get_db()
    if request.method == 'POST':
        try:
            data = validate_transaction(request.get_json())
        except ValueError as error:
            return jsonify(error=str(error)), 400
        with db:
            cursor = db.execute('''INSERT INTO transactions
                (user_id,kind,amount_paise,category_id,description,date,payment_method,notes)
                VALUES (?,?,?,?,?,?,?,?)''', (g.user['id'], *data.values()))
        row = db.execute(SELECT + ' WHERE t.id=? AND t.user_id=?', (cursor.lastrowid, g.user['id'])).fetchone()
        return jsonify(transaction=as_transaction(row)), 201
    try:
        where, args = filters()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        if page < 1 or not 1 <= per_page <= 100:
            raise ValueError('Invalid pagination.')
    except ValueError as error:
        return jsonify(error=str(error)), 400
    total = db.execute('SELECT COUNT(*) FROM transactions t' + where, args).fetchone()[0]
    rows = db.execute(SELECT + where + ' ORDER BY t.date DESC,t.id DESC LIMIT ? OFFSET ?',
                      [*args, per_page, (page - 1) * per_page]).fetchall()
    return jsonify(transactions=[as_transaction(r) for r in rows], total=total, page=page, per_page=per_page)


@bp.route('/api/transactions/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def transaction(record_id):
    db = get_db()
    row = db.execute(SELECT + ' WHERE t.id=? AND t.user_id=?', (record_id, g.user['id'])).fetchone()
    if row is None:
        return jsonify(error='Transaction not found.'), 404
    if request.method == 'GET':
        return jsonify(transaction=as_transaction(row))
    if request.method == 'DELETE':
        with db:
            db.execute('DELETE FROM transactions WHERE id=? AND user_id=?', (record_id, g.user['id']))
        return '', 204
    try:
        data = validate_transaction(request.get_json())
    except ValueError as error:
        return jsonify(error=str(error)), 400
    with db:
        db.execute('''UPDATE transactions SET kind=?,amount_paise=?,category_id=?,description=?,date=?,
                      payment_method=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?''',
                   (*data.values(), record_id, g.user['id']))
    return jsonify(transaction=as_transaction(db.execute(SELECT + ' WHERE t.id=? AND t.user_id=?',
                                                        (record_id, g.user['id'])).fetchone()))


@bp.get('/api/summary')
@login_required
def summary():
    try:
        month = request.args.get('month', date.today().strftime('%Y-%m'))
        start, end = month_range(month)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    db, uid = get_db(), g.user['id']
    totals = {'income': 0, 'expense': 0}
    for row in db.execute('SELECT kind,SUM(amount_paise) AS total FROM transactions WHERE user_id=? AND date>=? AND date<? GROUP BY kind', (uid, start, end)):
        totals[row['kind']] = row['total']
    balance = db.execute("SELECT COALESCE(SUM(CASE WHEN kind='income' THEN amount_paise ELSE -amount_paise END),0) FROM transactions WHERE user_id=? AND date<=?", (uid, date.today().isoformat())).fetchone()[0]
    categories = [dict(r) for r in db.execute('''SELECT c.id,c.name,SUM(t.amount_paise) AS total
        FROM transactions t JOIN categories c ON c.id=t.category_id
        WHERE t.user_id=? AND t.kind='expense' AND t.date>=? AND t.date<?
        GROUP BY c.id,c.name ORDER BY total DESC''', (uid, start, end))]
    first = date.fromisoformat(start)
    months = []
    for offset in range(5, -1, -1):
        serial = first.year * 12 + first.month - 1 - offset
        label = f'{serial // 12:04d}-{serial % 12 + 1:02d}'
        months.append({'month': label, 'income': 0, 'expense': 0})
    records = db.execute("SELECT substr(date,1,7) AS month,kind,SUM(amount_paise) AS total FROM transactions WHERE user_id=? AND date>=? AND date<? GROUP BY month,kind", (uid, months[0]['month'] + '-01', end))
    lookup = {m['month']: m for m in months}
    for row in records:
        lookup[row['month']][row['kind']] = row['total']
    return jsonify(month=month, income_paise=totals['income'], expense_paise=totals['expense'],
                   net_paise=totals['income'] - totals['expense'], balance_paise=balance,
                   categories=categories, trend=months)


@bp.get('/api/export')
@login_required
def export():
    try:
        where, args = filters()
    except ValueError as error:
        return jsonify(error=str(error)), 400
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['Date', 'Type', 'Description', 'Category', 'Amount (INR)', 'Payment method', 'Notes'])
    for row in get_db().execute(SELECT + where + ' ORDER BY t.date DESC,t.id DESC', args):
        t = as_transaction(row)
        # Prevent spreadsheet apps from treating user input as a formula.
        def safe(value):
            return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value
        writer.writerow([t['date'], t['kind'], safe(t['description']), t['category'], t['amount'], t['payment_method'], safe(t['notes'])])
    return Response('\ufeff' + output.getvalue(), mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=kharcha-transactions.csv'})


@bp.post('/api/parse')
@login_required
def parse():
    from .smart_entry import parse_entry
    body = request.get_json()
    if not isinstance(body, dict) or not isinstance(body.get('text'), str) or not 1 <= len(body['text'].strip()) <= 500:
        return jsonify(error='Enter a sentence up to 500 characters.'), 400
    if not rate_limit(f'parse:{g.user["id"]}', 15, 60):
        return jsonify(error='Please wait a minute before trying again.'), 429
    try:
        draft, source, notice = parse_entry(body['text'].strip(), bool(g.user['is_demo']))
        validate_transaction(draft)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return jsonify(draft=draft, source=source, notice=notice)
