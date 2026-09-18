import re
from datetime import date
from decimal import Decimal, InvalidOperation
from .db import get_db


def valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Use a date in YYYY-MM-DD format.')
    date.fromisoformat(value)
    return value


def validate_transaction(data):
    if not isinstance(data, dict):
        raise ValueError('Send a JSON object.')
    kind = data.get('kind')
    if kind not in ('income', 'expense'):
        raise ValueError('Choose income or expense.')
    raw = str(data.get('amount', ''))
    if not re.fullmatch(r'\d{1,10}(\.\d{1,2})?', raw):
        raise ValueError('Enter a positive amount with at most two decimal places.')
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise ValueError('Enter a valid amount.') from None
    if not 0 < amount <= 1_000_000_000:
        raise ValueError('Amount must be between ₹0.01 and ₹1,00,00,00,000.')
    category_id = data.get('category_id')
    if isinstance(category_id, bool) or not isinstance(category_id, int):
        raise ValueError('Choose a category.')
    if not get_db().execute('SELECT 1 FROM categories WHERE id=? AND kind=?', (category_id, kind)).fetchone():
        raise ValueError('Category must match the transaction type.')
    description = data.get('description')
    notes = data.get('notes', '')
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 120:
        raise ValueError('Description must contain 1–120 characters.')
    if not isinstance(notes, str) or len(notes) > 500:
        raise ValueError('Notes must be at most 500 characters.')
    payment = data.get('payment_method', 'UPI')
    if payment not in ('UPI', 'Cash', 'Card', 'Bank transfer'):
        raise ValueError('Choose a valid payment method.')
    return dict(kind=kind, amount_paise=int(amount * 100), category_id=category_id,
                description=description.strip(), date=valid_date(data.get('date')),
                payment_method=payment, notes=notes.strip())
