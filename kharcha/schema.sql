PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 60),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
    UNIQUE(id, kind), UNIQUE(name, kind)
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
    amount_paise INTEGER NOT NULL CHECK(amount_paise > 0 AND amount_paise <= 100000000000),
    category_id INTEGER NOT NULL,
    description TEXT NOT NULL CHECK(length(description) BETWEEN 1 AND 120),
    date TEXT NOT NULL CHECK(length(date) = 10),
    payment_method TEXT NOT NULL CHECK(payment_method IN ('UPI','Cash','Card','Bank transfer')),
    notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 500),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id, kind) REFERENCES categories(id, kind)
);
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, date DESC, id DESC);
CREATE TABLE IF NOT EXISTS rate_events (
    id INTEGER PRIMARY KEY,
    bucket TEXT NOT NULL,
    occurred_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_events_bucket_time ON rate_events(bucket, occurred_at);
INSERT OR IGNORE INTO categories(id,name,kind) VALUES
 (1,'Food & drinks','expense'),(2,'Transport','expense'),(3,'Shopping','expense'),
 (4,'Bills & rent','expense'),(5,'Entertainment','expense'),(6,'Education','expense'),
 (7,'Health','expense'),(8,'Other expense','expense'),(9,'Salary','income'),
 (10,'Freelance','income'),(11,'Allowance','income'),(12,'Other income','income');
PRAGMA user_version = 1;
