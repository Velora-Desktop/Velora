import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import QSettings

from app.data.user_repository import USER_MIGRATIONS, UserRepository
from app.database.migration_runner import MigrationRunner
from app.models.game import GameData
from app.services.data_backup_service import BackupValidationError, DataBackupService


class Aw008DataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.user_db = self.root / "user.db"
        self.catalog_db = self.root / "catalog.db"
        with closing(sqlite3.connect(self.catalog_db)) as connection:
            connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)")
            connection.execute("INSERT INTO metadata VALUES('schema_version','4')")
            connection.execute("CREATE TABLE catalog_items(catalog_id TEXT PRIMARY KEY)")
            connection.commit()
        self.repository = UserRepository(self.user_db)
        self.settings = QSettings(str(self.root / "settings.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("hide_adult_content", True)
        self.service = DataBackupService(
            self.user_db,
            self.catalog_db,
            self.settings,
            backups_dir=self.root / "backups",
            user_images_dir=self.root / "images",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_export_and_full_import_restore_user_data(self) -> None:
        game = GameData("Test", "8.0", "7.5", "ПРОШЁЛ", "Dev", "2020", "PC", "1P", catalog_id="g-test-001")
        game.playtime_hours = 12.5
        self.repository.save_game_state(game)
        backup = self.service.export_backup()
        self.assertRegex(backup.name, r"Velora_Backup_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.zip")
        with zipfile.ZipFile(backup) as archive:
            metadata = json.loads(archive.read("metadata.json"))
            self.assertIn("user.db", metadata["files"])
            self.assertIn("settings.json", metadata["files"])
        with closing(sqlite3.connect(self.user_db)) as connection:
            connection.execute("DELETE FROM user_game_state")
            connection.commit()
        self.settings.setValue("hide_adult_content", False)
        self.service.import_backup(backup)
        with closing(sqlite3.connect(self.user_db)) as connection:
            row = connection.execute("SELECT personal_score,playtime_hours,status FROM user_game_state WHERE catalog_id='g-test-001'").fetchone()
        self.assertEqual(row, (7.5, 12.5, "ПРОШЁЛ"))
        self.assertTrue(self.settings.value("hide_adult_content", type=bool))
        self.assertTrue(any((self.root / "backups").glob("Velora_Backup_*.zip")))

    def test_invalid_backup_is_rejected_without_changing_database(self) -> None:
        before = self.user_db.read_bytes()
        bad = self.root / "bad.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("metadata.json", "{}")
        with self.assertRaises(BackupValidationError):
            self.service.import_backup(bad)
        self.assertEqual(self.user_db.read_bytes(), before)

    def test_integrity_and_backup_before_atomic_migration(self) -> None:
        migrations = self.root / "migrations"; migrations.mkdir()
        (migrations / "001_initial.sql").write_text("CREATE TABLE sample(value TEXT);", encoding="utf-8")
        database = self.root / "migration.db"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE legacy(value TEXT)")
            connection.commit()
        runner = MigrationRunner(migrations, self.root / "migration_backups")
        self.assertEqual(runner.migrate(database), ["001"])
        self.assertTrue(any((self.root / "migration_backups").glob("before_migration_*.db")))
        self.assertEqual(self.service.integrity_check(database)[0], True)
        self.assertEqual(self.service.versions()["catalog_schema"], "4")

    def test_metrics_are_type_specific_and_history_is_persistent(self) -> None:
        game = GameData("Game", "8.0", "8.0", "ПРОХОЖУ", "Dev", "2020", "PC", "1P", catalog_id="g-1")
        game.playtime_hours = 4.5
        self.repository.save_game_state(game)
        film = GameData("Film", "8.0", "8.0", "ПОСМОТРЕЛ", "Director", "2020", "Cinema", "", catalog_id="f-1", media_type="Фильмы")
        film.watch_count = 2
        self.repository.save_game_state(film)
        series = GameData("Series", "8.0", "8.0", "СМОТРЮ", "Creator", "2020", "Stream", "", catalog_id="s-1", media_type="Сериалы")
        series.season_number, series.episode_number = 2, 4
        self.repository.save_game_state(series)
        program = GameData("App", "8.0", "8.0", "ИСПОЛЬЗУЮ", "Dev", "2020", "Windows", "", catalog_id="p-1", media_type="Программы")
        program.playtime_hours = 99
        self.repository.save_game_state(program)
        loaded = [game, film, series, program]
        for item in loaded:
            item.playtime_hours = 0
        self.repository.apply_game_states(loaded)
        self.assertEqual(game.playtime_hours, 4.5)
        self.assertEqual(film.watch_count, 2)
        self.assertEqual((series.season_number, series.episode_number), (2, 4))
        self.assertEqual(program.playtime_hours, 0)
        self.assertTrue(self.repository.activity_for("g-1"))

    def test_aw00711_user_database_migrates_without_losing_state(self) -> None:
        legacy = self.root / "legacy_user.db"
        with closing(sqlite3.connect(legacy)) as connection:
            connection.executescript(
                """
                CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP);
                INSERT INTO schema_migrations(version) VALUES('001'),('002'),('003'),('004');
                CREATE TABLE local_profile(profile_id INTEGER PRIMARY KEY,display_name TEXT,bio TEXT,avatar_path TEXT,created_at TEXT,updated_at TEXT);
                INSERT INTO local_profile VALUES(1,'Tester','','','now','now');
                CREATE TABLE user_game_state(catalog_id TEXT PRIMARY KEY,personal_score REAL,status TEXT,playtime_hours REAL DEFAULT 0,favorite INTEGER DEFAULT 0,rating_criteria_json TEXT DEFAULT '{}',updated_at TEXT,hidden INTEGER DEFAULT 0,watch_count INTEGER DEFAULT 0,season_number INTEGER DEFAULT 0,episode_number INTEGER DEFAULT 0);
                INSERT INTO user_game_state VALUES('g-old',8.5,'ПРОШЁЛ',22,1,'{}','now',0,0,0,0);
                CREATE TABLE user_activity(id INTEGER PRIMARY KEY AUTOINCREMENT,catalog_id TEXT,event_type TEXT,old_value TEXT,new_value TEXT,total_playtime REAL,note TEXT DEFAULT '',created_at TEXT);
                CREATE TABLE series_episode_state(catalog_id TEXT,season_number INTEGER,episode_number INTEGER,state TEXT,updated_at TEXT,PRIMARY KEY(catalog_id,season_number,episode_number));
                """
            )
            connection.commit()
        MigrationRunner(USER_MIGRATIONS, self.root / "legacy_backups").migrate(legacy)
        with closing(sqlite3.connect(legacy)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(user_game_state)")}
            row = connection.execute("SELECT personal_score,playtime_hours,favorite FROM user_game_state WHERE catalog_id='g-old'").fetchone()
        self.assertTrue({"interaction_started_at", "interaction_completed_at"}.issubset(columns))
        self.assertEqual(row, (8.5, 22.0, 1))


if __name__ == "__main__":
    unittest.main()
