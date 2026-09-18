"""Fictional sample records. Only inserted when a visitor chooses the demo."""
from datetime import date, timedelta


def seed_demo(db, user_id):
    today = date.today()
    samples = [
        (0, 'expense', 18000, 1, 'Coffee & a catch-up', 'UPI'),
        (1, 'expense', 34900, 1, 'Dinner at the dhaba', 'UPI'),
        (2, 'expense', 19900, 5, 'Spotify Premium', 'Card'),
        (3, 'expense', 12000, 2, 'Auto to campus', 'Cash'),
        (4, 'expense', 89900, 3, 'A new everyday tee', 'UPI'),
        (5, 'income', 450000, 10, 'Website freelance work', 'Bank transfer'),
        (6, 'expense', 65000, 6, 'Python course', 'Card'),
        (7, 'expense', 24900, 1, 'Late-night pizza', 'UPI'),
        (8, 'expense', 29900, 4, 'Mobile recharge', 'UPI'),
        (10, 'expense', 32000, 1, 'Groceries', 'UPI'),
        (11, 'expense', 8500, 2, 'Bus fare', 'Cash'),
        (12, 'expense', 15000, 7, 'Pharmacy', 'UPI'),
        (13, 'income', 1200000, 11, 'Monthly allowance', 'Bank transfer'),
        (14, 'expense', 350000, 4, 'Room rent', 'Bank transfer'),
        (18, 'expense', 42000, 1, 'Lunch with friends', 'UPI'),
        (23, 'expense', 120000, 3, 'Books & supplies', 'Card'),
        (29, 'income', 1000000, 11, 'Monthly allowance', 'Bank transfer'),
        (32, 'expense', 350000, 4, 'Room rent', 'Bank transfer'),
        (35, 'expense', 170000, 1, 'Groceries & meals', 'UPI'),
        (41, 'expense', 84000, 2, 'Travel home', 'UPI'),
        (60, 'income', 1000000, 11, 'Monthly allowance', 'Bank transfer'),
        (61, 'expense', 580000, 4, 'Rent & utilities', 'Bank transfer'),
        (90, 'income', 1000000, 11, 'Monthly allowance', 'Bank transfer'),
        (91, 'expense', 630000, 4, 'Rent & utilities', 'Bank transfer'),
        (120, 'income', 1000000, 11, 'Monthly allowance', 'Bank transfer'),
        (121, 'expense', 510000, 4, 'Rent & utilities', 'Bank transfer'),
        (150, 'income', 1000000, 11, 'Monthly allowance', 'Bank transfer'),
        (151, 'expense', 720000, 4, 'Rent & utilities', 'Bank transfer'),
    ]
    db.executemany('''INSERT INTO transactions(user_id,kind,amount_paise,category_id,description,date,payment_method)
                      VALUES (?,?,?,?,?,?,?)''',
                   [(user_id, k, a, c, d, (today - timedelta(days=offset)).isoformat(), p)
                    for offset, k, a, c, d, p in samples])
