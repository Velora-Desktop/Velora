CREATE TABLE IF NOT EXISTS smart_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT '',
    rules_json TEXT NOT NULL DEFAULT '{}',
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_notes (
    catalog_id TEXT PRIMARY KEY,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    color TEXT NOT NULL DEFAULT '#8B2CF5',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_item_tags (
    catalog_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL REFERENCES user_tags(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(catalog_id, tag_id)
);

CREATE TABLE IF NOT EXISTS user_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT '',
    metric TEXT NOT NULL,
    target_value REAL NOT NULL,
    current_value REAL NOT NULL DEFAULT 0,
    deadline TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interaction_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_id TEXT NOT NULL,
    session_type TEXT NOT NULL,
    sequence_number INTEGER NOT NULL DEFAULT 1,
    value REAL NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_smart_lists_type ON smart_lists(media_type);
CREATE INDEX IF NOT EXISTS idx_user_item_tags_catalog ON user_item_tags(catalog_id);
CREATE INDEX IF NOT EXISTS idx_interaction_sessions_catalog_time ON interaction_sessions(catalog_id, occurred_at);
