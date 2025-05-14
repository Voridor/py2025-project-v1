import csv
import datetime
import json
import os
import shutil
import zipfile
from typing import Iterator, Dict, Optional


class Logger:
    def __init__(self, config_path: str):
        """
        Inicjalizuje logger na podstawie pliku JSON.
        :param config_path: Ścieżka do pliku konfiguracyjnego (.json)
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.log_dir = self.config.get("log_dir", "./logs")
        self.filename_pattern = self.config.get("filename_pattern", "sensors_%Y%m%d.csv")
        self.buffer_size = self.config.get("buffer_size", 10)  # Domyślnie 10 dla testów, specyfikacja mówi 200
        self.rotate_every_hours = self.config.get("rotate_every_hours")
        self.max_size_mb = self.config.get("max_size_mb")
        self.rotate_after_lines = self.config.get("rotate_after_lines")
        self.retention_days = self.config.get("retention_days")
        self.compress_archive = self.config.get("compress_archive", True)  # Domyślnie kompresuj

        self.archive_dir = os.path.join(self.log_dir, "archive")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

        self.buffer = []
        self.current_file_path = None
        self.current_file_writer = None
        self.current_file_handle = None
        self.current_file_lines = 0
        self.last_rotation_time = datetime.datetime.now()

    def start(self) -> None:
        """
        Otwiera nowy plik CSV do logowania. Jeśli plik jest nowy, zapisuje nagłówek.
        """
        if self.current_file_handle:
            self.stop()  # Zamknij poprzedni plik jeśli istnieje

        timestamp = datetime.datetime.now()
        self.current_file_path = os.path.join(self.log_dir, timestamp.strftime(self.filename_pattern))

        file_exists = os.path.exists(self.current_file_path)
        # Otwieramy w trybie append ('a'), żeby nie nadpisywać istniejących danych,
        # jeśli plik o tej samej nazwie (np. z tego samego dnia) już istnieje
        # i nie został jeszcze zarchiwizowany (np. po restarcie aplikacji).
        self.current_file_handle = open(self.current_file_path, 'a', newline='', encoding='utf-8')
        self.current_file_writer = csv.writer(self.current_file_handle)

        if not file_exists or os.path.getsize(self.current_file_path) == 0:
            self.current_file_writer.writerow(["timestamp", "sensor_id", "value", "unit"])
            self.current_file_lines = 1  # Nagłówek
        else:
            # Jeśli plik istnieje i nie jest pusty, policz linie (może być niedokładne przy złożonych CSV)
            # Dla uproszczenia zakładamy, że odczytujemy wszystkie linie przy starcie, jeśli plik istnieje
            # W bardziej zaawansowanym rozwiązaniu można by to zoptymalizować
            with open(self.current_file_path, 'r', newline='', encoding='utf-8') as f_count:
                reader = csv.reader(f_count)
                self.current_file_lines = sum(1 for row in reader)

        self.last_rotation_time = datetime.datetime.now()  # Resetujemy czas ostatniej rotacji

    def stop(self) -> None:
        """
        Wymusza zapis bufora i zamyka bieżący plik.
        """
        self._flush_buffer()
        if self.current_file_handle:
            self.current_file_handle.close()
            self.current_file_handle = None
            self.current_file_writer = None
            self.current_file_path = None
            self.current_file_lines = 0

    def log_reading(
            self,
            sensor_id: str,
            timestamp: datetime.datetime,  # Oczekujemy obiektu datetime
            value: float,
            unit: str
    ) -> None:
        """
        Dodaje wpis do bufora i ewentualnie wykonuje rotację pliku.
        """
        if not self.current_file_handle:
            # Jeśli plik nie jest otwarty (np. po pierwszym uruchomieniu lub po rotacji)
            self.start()

        self.buffer.append([timestamp.isoformat(), sensor_id, value, unit])

        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()

        self._check_and_perform_rotation()

    def _flush_buffer(self) -> None:
        """Wewnętrzna metoda do zapisu bufora do pliku."""
        if self.current_file_writer and self.buffer:
            self.current_file_writer.writerows(self.buffer)
            self.current_file_lines += len(self.buffer)
            self.buffer.clear()
            if self.current_file_handle:  # Upewnij się, że plik jest otwarty
                self.current_file_handle.flush()  # Wymuś zapis na dysk

    def _check_and_perform_rotation(self) -> None:
        """Sprawdza warunki rotacji i wykonuje ją w razie potrzeby."""
        if not self.current_file_path:  # Nie ma czego rotować
            return

        perform_rotation = False
        now = datetime.datetime.now()

        # 1. Interwał czasowy
        if self.rotate_every_hours:
            if (now - self.last_rotation_time).total_seconds() >= self.rotate_every_hours * 3600:
                perform_rotation = True
                # print(f"DEBUG: Rotacja przez czas: {now}, ostatnia: {self.last_rotation_time}")

        # 2. Rozmiar pliku
        if not perform_rotation and self.max_size_mb:
            try:
                current_size_mb = os.path.getsize(self.current_file_path) / (1024 * 1024)
                if current_size_mb >= self.max_size_mb:
                    perform_rotation = True
                    # print(f"DEBUG: Rotacja przez rozmiar: {current_size_mb} MB")
            except FileNotFoundError:
                # Plik mógł zostać usunięty lub przeniesiony w międzyczasie
                pass

        # 3. Liczba wpisów
        if not perform_rotation and self.rotate_after_lines:
            if self.current_file_lines >= self.rotate_after_lines:
                perform_rotation = True
                # print(f"DEBUG: Rotacja przez liczbę linii: {self.current_file_lines}")

        if perform_rotation:
            self._rotate()

    def _rotate(self) -> None:
        """Wykonuje proces rotacji: archiwizuje stary plik, czyści stare archiwa, otwiera nowy plik."""
        # print(f"DEBUG: Rozpoczynanie rotacji dla {self.current_file_path}")
        old_file_path = self.current_file_path

        self.stop()  # Zapisuje bufor i zamyka bieżący plik

        if old_file_path and os.path.exists(old_file_path):  # Sprawdź czy plik faktycznie istnieje
            self._archive(old_file_path)

        self._clean_old_archives()

        self.start()  # Otwiera nowy plik logów
        self.last_rotation_time = datetime.datetime.now()  # Aktualizacja czasu ostatniej rotacji
        # print("DEBUG: Rotacja zakończona, nowy plik otwarty.")

    def _archive(self, file_path_to_archive: str) -> None:
        """Archiwizuje podany plik."""
        if not os.path.exists(file_path_to_archive):
            # print(f"DEBUG: Plik {file_path_to_archive} nie istnieje, pomijanie archiwizacji.")
            return

        base_filename = os.path.basename(file_path_to_archive)
        archive_target_path = os.path.join(self.archive_dir, base_filename)

        if self.compress_archive:
            archive_target_path += ".zip"
            try:
                with zipfile.ZipFile(archive_target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(file_path_to_archive, base_filename)
                os.remove(file_path_to_archive)  # Usuń oryginał po skompresowaniu
                # print(f"DEBUG: Zarchiwizowano i skompresowano {file_path_to_archive} do {archive_target_path}")
            except Exception as e:
                print(f"Błąd podczas kompresji pliku {file_path_to_archive}: {e}")
                # Jeśli kompresja się nie uda, spróbuj przenieść plik bez kompresji
                try:
                    shutil.move(file_path_to_archive, os.path.join(self.archive_dir, base_filename))
                    # print(f"DEBUG: Przeniesiono (bez kompresji) {file_path_to_archive} do archiwum po błędzie kompresji.")
                except Exception as e_move:
                    print(f"Błąd podczas przenoszenia pliku {file_path_to_archive} do archiwum: {e_move}")
        else:
            try:
                shutil.move(file_path_to_archive, archive_target_path)
                # print(f"DEBUG: Zarchiwizowano (bez kompresji) {file_path_to_archive} do {archive_target_path}")
            except Exception as e:
                print(f"Błąd podczas przenoszenia pliku {file_path_to_archive} do archiwum: {e}")

    def _clean_old_archives(self) -> None:
        """Usuwa archiwa starsze niż `retention_days`."""
        if self.retention_days is None:
            return

        now = datetime.datetime.now()
        cutoff_date = now - datetime.timedelta(days=self.retention_days)

        for filename in os.listdir(self.archive_dir):
            file_path = os.path.join(self.archive_dir, filename)
            try:
                file_mod_time_dt = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mod_time_dt < cutoff_date:
                    os.remove(file_path)
                    # print(f"DEBUG: Usunięto stare archiwum: {file_path}")
            except OSError as e:
                print(f"Błąd podczas usuwania starego archiwum {file_path}: {e}")
            except Exception as e:
                print(f"Nieoczekiwany błąd podczas przetwarzania archiwum {file_path}: {e}")

    def read_logs(
            self,
            start_dt: datetime.datetime,  # Zmieniono nazwę dla jasności, że to datetime
            end_dt: datetime.datetime,  # Zmieniono nazwę dla jasności, że to datetime
            sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Pobiera wpisy z logów zadanego zakresu i opcjonalnie konkretnego czujnika.
        Iteruje przez pliki .csv w log_dir/ i archiwa .zip w log_dir/archive/.
        """
        files_to_check = []

        # 1. Sprawdź aktualnie otwarty plik (jeśli istnieje i nie jest pusty)
        if self.current_file_path and os.path.exists(self.current_file_path) and os.path.getsize(
                self.current_file_path) > 0:
            files_to_check.append(self.current_file_path)

        # 2. Sprawdź pliki w katalogu log_dir (inne niż aktualny)
        for filename in os.listdir(self.log_dir):
            if filename.endswith(".csv"):
                file_path = os.path.join(self.log_dir, filename)
                if file_path != self.current_file_path:  # Unikaj duplikatu
                    files_to_check.append(file_path)

        # 3. Sprawdź pliki w katalogu archive_dir
        for filename in os.listdir(self.archive_dir):
            file_path = os.path.join(self.archive_dir, filename)
            files_to_check.append(file_path)

        # Sortuj pliki, aby próbować przetwarzać je w kolejności chronologicznej (na podstawie nazwy)
        # To jest heurystyka, lepsze byłoby parsowanie daty z nazwy pliku, jeśli wzorzec na to pozwala.
        files_to_check.sort()

        for file_path in files_to_check:
            try:
                if file_path.endswith(".csv"):
                    with open(file_path, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            try:
                                timestamp_str = row.get("timestamp")
                                if not timestamp_str: continue  # Pomiń wiersze bez timestamp

                                row_time = datetime.datetime.fromisoformat(timestamp_str)
                                if start_dt <= row_time <= end_dt:
                                    if sensor_id is None or row.get("sensor_id") == sensor_id:
                                        yield {
                                            "timestamp": row_time,
                                            "sensor_id": row.get("sensor_id"),
                                            "value": float(row.get("value", 0.0)),
                                            # Dodaj domyślną wartość w razie braku
                                            "unit": row.get("unit")
                                        }
                            except (ValueError, TypeError) as e_parse:
                                # print(f"Błąd parsowania wiersza w {file_path}: {row} - {e_parse}")
                                continue  # Pomiń błędny wiersz
                elif file_path.endswith(".zip"):
                    with zipfile.ZipFile(file_path, 'r') as zipf:
                        for csv_filename_in_zip in zipf.namelist():
                            if csv_filename_in_zip.endswith(".csv"):  # Upewnij się, że to CSV w ZIPie
                                with zipf.open(csv_filename_in_zip, 'r') as f_bytes:
                                    # Potrzebujemy zdekodować bajty do tekstu
                                    # Zakładamy UTF-8, co jest częste
                                    import io
                                    f_text = io.TextIOWrapper(f_bytes, encoding='utf-8')
                                    reader = csv.DictReader(f_text)
                                    for row in reader:
                                        try:
                                            timestamp_str = row.get("timestamp")
                                            if not timestamp_str: continue

                                            row_time = datetime.datetime.fromisoformat(timestamp_str)
                                            if start_dt <= row_time <= end_dt:
                                                if sensor_id is None or row.get("sensor_id") == sensor_id:
                                                    yield {
                                                        "timestamp": row_time,
                                                        "sensor_id": row.get("sensor_id"),
                                                        "value": float(row.get("value", 0.0)),
                                                        "unit": row.get("unit")
                                                    }
                                        except (ValueError, TypeError) as e_parse:
                                            # print(f"Błąd parsowania wiersza w {csv_filename_in_zip} (z {file_path}): {row} - {e_parse}")
                                            continue
            except FileNotFoundError:
                # Plik mógł zostać usunięty/przeniesiony od czasu listowania
                # print(f"Plik {file_path} nie znaleziony podczas odczytu logów.")
                continue
            except Exception as e:
                print(f"Ogólny błąd podczas przetwarzania pliku {file_path}: {e}")
                continue