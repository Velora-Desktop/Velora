CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog_items (
    catalog_id TEXT PRIMARY KEY,
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    subgroup TEXT NOT NULL,
    age_rating INTEGER NOT NULL,
    general_score REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_catalog_location
ON catalog_items(media_type, category, subgroup, title);
