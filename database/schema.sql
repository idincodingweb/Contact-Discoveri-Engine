PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT,
    domain        TEXT UNIQUE,
    website       TEXT,
    country       TEXT,
    niche         TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    contact_name  TEXT,
    role          TEXT,
    role_priority INTEGER DEFAULT 99,
    email         TEXT,
    whatsapp      TEXT,
    telegram      TEXT,
    linkedin      TEXT,
    instagram     TEXT,
    facebook      TEXT,
    twitter       TEXT,
    tiktok        TEXT,
    youtube       TEXT,
    source_url    TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(company_id, contact_name, email)
);

CREATE TABLE IF NOT EXISTS discoveries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    kind          TEXT,                 -- email | whatsapp | telegram | linkedin | instagram | facebook | twitter | tiktok | youtube | phone
    value         TEXT,
    source_url    TEXT,
    confidence    REAL DEFAULT 0.5,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(company_id, kind, value)
);

CREATE TABLE IF NOT EXISTS crawl_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT UNIQUE,
    status_code   INTEGER,
    fetched_at    TEXT DEFAULT (datetime('now')),
    bytes         INTEGER,
    error         TEXT
);

CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_discoveries_company ON discoveries(company_id);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_url ON crawl_logs(url);
