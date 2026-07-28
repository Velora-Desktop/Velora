-- AW0.10: ordered franchise timelines, including unreleased/external entries.
ALTER TABLE catalog_items ADD COLUMN franchise_name TEXT NOT NULL DEFAULT '';
ALTER TABLE catalog_items ADD COLUMN chronology_json TEXT NOT NULL DEFAULT '[]';
