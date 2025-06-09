import unittest
import tempfile
import shutil
import os
import json
import datetime
import time
from logger import Logger  # Zakładamy, że twój kod to logger.py


class TestLogger(unittest.TestCase):
    def setUp(self):
        # Utwórz tymczasowy katalog dla logów
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")

        self.config = {
            "log_dir": self.temp_dir,
            "filename_pattern": "testlog_%Y%m%d.csv",
            "buffer_size": 2,
            "rotate_every_hours": 0.001,  # około 3.6 sekundy dla szybkiego testu
            "max_size_mb": 1,
            "rotate_after_lines": 5,
            "retention_days": 1,
            "compress_archive": True
        }

        with open(self.config_path, 'w') as f:
            json.dump(self.config, f)

        self.logger = Logger(self.config_path)
        self.logger.start()

    def tearDown(self):
        self.logger.stop()
        shutil.rmtree(self.temp_dir)

    def test_log_and_flush(self):
        # Sprawdza, czy dane są zapisywane do pliku po przekroczeniu bufora
        now = datetime.datetime.now()
        self.logger.log_reading("sensor_1", now, 23.5, "C")
        self.logger.log_reading("sensor_1", now, 23.6, "C")  # To powinno wypchnąć bufor
        self.logger.stop()

        log_files = [f for f in os.listdir(self.temp_dir) if f.endswith(".csv")]
        self.assertTrue(log_files)

        path = os.path.join(self.temp_dir, log_files[0])
        with open(path, 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)  # nagłówek + 2 wpisy

    def test_rotation_by_time(self):
        now = datetime.datetime.now()
        self.logger.log_reading("sensor_1", now, 20.0, "C")
        self.logger.log_reading("sensor_1", now, 21.0, "C")
        time.sleep(4)  # pozwól rotacji na zadziałanie przez czas
        self.logger.log_reading("sensor_1", now, 22.0, "C")
        self.logger.stop()

        archive_dir = os.path.join(self.temp_dir, "archive")
        self.assertTrue(os.path.exists(archive_dir))
        archived_files = [f for f in os.listdir(archive_dir) if f.endswith(".zip")]
        self.assertGreaterEqual(len(archived_files), 1)

    def test_read_logs(self):
        now = datetime.datetime.now()
        self.logger.log_reading("sensor_2", now, 50.1, "Pa")
        self.logger.log_reading("sensor_2", now, 50.2, "Pa")
        self.logger.stop()

        results = list(self.logger.read_logs(now - datetime.timedelta(seconds=1),
                                             now + datetime.timedelta(seconds=1)))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r['sensor_id'] == "sensor_2" for r in results))

    def test_rotation_by_lines(self):
        now = datetime.datetime.now()
        for _ in range(6):  # więcej niż rotate_after_lines
            self.logger.log_reading("sensor_x", now, 42.0, "unit")
        self.logger.stop()

        archive_dir = os.path.join(self.temp_dir, "archive")
        archived_files = [f for f in os.listdir(archive_dir)]
        self.assertTrue(any(".zip" in f for f in archived_files))

    def test_retention_deletes_old_archives(self):
        # Stwórz sztucznie plik w archiwum z datą modyfikacji > 1 dzień temu
        archive_dir = os.path.join(self.temp_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        old_file_path = os.path.join(archive_dir, "old_log.csv.zip")
        with open(old_file_path, 'w') as f:
            f.write("dummy")

        old_time = datetime.datetime.timestamp(datetime.datetime.now() - datetime.timedelta(days=2))
        os.utime(old_file_path, (old_time, old_time))

        self.logger._clean_old_archives()
        self.assertFalse(os.path.exists(old_file_path))


if __name__ == "__main__":
    import time  # tylko do testu rotacji czasowej
    unittest.main()
