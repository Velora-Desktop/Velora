CREATE TABLE IF NOT EXISTS series_episode_state (
    catalog_id TEXT NOT NULL,
    season_number INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'unwatched',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (catalog_id, season_number, episode_number)
);

CREATE INDEX IF NOT EXISTS idx_series_episode_catalog
ON series_episode_state(catalog_id, season_number, episode_number);
