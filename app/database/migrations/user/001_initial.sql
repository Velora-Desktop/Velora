CREATE TABLE IF NOT EXISTS local_profile (
    profile_id INTEGER PRIMARY KEY CHECK(profile_id = 1),
    display_name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    avatar_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_game_state (
    catalog_id TEXT PRIMARY KEY,
    personal_score REAL,
    status TEXT,
    playtime_hours REAL NOT NULL DEFAULT 0,
    favorite INTEGER NOT NULL DEFAULT 0,
    rating_criteria_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    hidden INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    total_playtime REAL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_activity_catalog_time
ON user_activity(catalog_id, created_at);
