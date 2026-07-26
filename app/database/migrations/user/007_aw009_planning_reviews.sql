CREATE TABLE IF NOT EXISTS manual_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    cover_path TEXT NOT NULL DEFAULT '',
    is_ranked INTEGER NOT NULL DEFAULT 0,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS manual_list_items (
    list_id INTEGER NOT NULL REFERENCES manual_lists(id) ON DELETE CASCADE,
    catalog_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    previous_position INTEGER,
    added_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(list_id, catalog_id)
);

CREATE TABLE IF NOT EXISTS queue_items (
    catalog_id TEXT PRIMARY KEY,
    position INTEGER NOT NULL,
    plan_kind TEXT NOT NULL DEFAULT 'Без даты',
    planned_date TEXT,
    priority TEXT NOT NULL DEFAULT 'Обычный',
    reason TEXT NOT NULL DEFAULT '',
    goal_id INTEGER REFERENCES user_goals(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS review_drafts (
    catalog_id TEXT PRIMARY KEY,
    template_id INTEGER REFERENCES review_templates(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    criteria_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_id TEXT NOT NULL,
    body TEXT NOT NULL,
    progress_value TEXT NOT NULL DEFAULT '',
    score REAL,
    image_path TEXT NOT NULL DEFAULT '',
    session_id INTEGER REFERENCES interaction_sessions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS saved_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT '',
    filters_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS archived_items (
    catalog_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL DEFAULT '',
    archived_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trash_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    deleted_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pinned_items (
    slot TEXT PRIMARY KEY,
    catalog_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_manual_list_items_position ON manual_list_items(list_id, position);
CREATE INDEX IF NOT EXISTS idx_queue_items_position ON queue_items(position);
CREATE INDEX IF NOT EXISTS idx_review_drafts_updated ON review_drafts(updated_at);
CREATE INDEX IF NOT EXISTS idx_journal_catalog_time ON journal_entries(catalog_id, created_at);
CREATE INDEX IF NOT EXISTS idx_trash_expiry ON trash_items(expires_at);
