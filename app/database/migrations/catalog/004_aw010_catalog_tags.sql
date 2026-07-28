-- AW0.10: official catalog tags are separate from personal tags in user.db.
ALTER TABLE catalog_items
ADD COLUMN catalog_tags_json TEXT NOT NULL DEFAULT '[]';
