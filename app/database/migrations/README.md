# SQLite migrations

`catalog/` contains the official catalog schema. `user/` contains local,
user-owned data. Never place personal state in catalog migrations.

Migration files are append-only. Once released, an existing numbered file must
not be edited; create the next number instead.
