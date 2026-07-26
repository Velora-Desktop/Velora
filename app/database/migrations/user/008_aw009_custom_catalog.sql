CREATE TABLE IF NOT EXISTS custom_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_catalog_items (
    catalog_id TEXT PRIMARY KEY,
    section_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    subgroup TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    creator TEXT NOT NULL DEFAULT '',
    release_year INTEGER,
    cover_path TEXT NOT NULL DEFAULT '',
    age_rating INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY(section_id) REFERENCES custom_sections(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_custom_catalog_location
ON custom_catalog_items(section_id, category, subgroup, title);
