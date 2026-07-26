CREATE TABLE IF NOT EXISTS custom_catalog_branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    subgroup TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(section_id) REFERENCES custom_sections(id) ON DELETE CASCADE,
    UNIQUE(section_id, category, subgroup)
);

CREATE INDEX IF NOT EXISTS idx_custom_catalog_branches_location
ON custom_catalog_branches(section_id, category, subgroup);
