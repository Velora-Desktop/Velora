ALTER TABLE catalog_items ADD COLUMN budget_amount REAL;
ALTER TABLE catalog_items ADD COLUMN budget_currency TEXT NOT NULL DEFAULT '';
