import time
import datetime
from Logger import Logger
from sensor import sensor, TemperatureSensor, HumiditySensor, PressureSensor

if __name__ == "__main__":
    # 1. Inicjalizacja Loggera
    logger = Logger(config_path="config.json")
    logger.start()
    print(f"Logger uruchomiony. Logi będą zapisywane w: {logger.log_dir}")

    # 2. Tworzenie instancji sensorów
    temp_sensor = TemperatureSensor(sensor_id="temp_salon_01", name="Temperatura Salon", unit="°C", min_value=-10,
                                    max_value=40,frequency=5)
    humidity_sensor = HumiditySensor(sensor_id="wilg_kuchnia_01", name="Wilgotność Kuchnia", unit="%", min_value=30,
                                     max_value=70,frequency=5)
    pressure_sensor = PressureSensor(sensor_id="cisn_zew_01", name="Ciśnienie Zewnętrzne", unit="hPa", min_value=950,
                                     max_value=1050,frequency=5)

    sensors_list = [temp_sensor, humidity_sensor, pressure_sensor]

    # 3. Główna pętla symulacji (sekwencyjna)
    simulation_duration_seconds = 60
    read_interval_seconds = 5

    print(f"Rozpoczynam sekwencyjną symulację na {simulation_duration_seconds} sekund...")
    start_sim_time = time.time()

    try:
        while time.time() - start_sim_time < simulation_duration_seconds:
            current_timestamp = datetime.datetime.now()
            print(f"\n--- Odczyty o {current_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ---")

            for s in sensors_list:
                if s.active:
                    value = s.read_value()
                    if value is not None:
                        print(f"Odczyt z {s.name} ({s.sensor_id}): {value:.2f} {s.unit}")
                        # Bezpośrednie wywołanie logowania
                        logger.log_reading(
                            sensor_id=s.sensor_id,
                            timestamp=current_timestamp,
                            value=value,
                            unit=s.unit
                        )
                    else:
                        print(
                            f"Brak odczytu z {s.name} ({s.sensor_id}) - czujnik może być nieaktywny lub błąd odczytu.")

            # Poczekaj przed następną serią odczytów
            time.sleep(read_interval_seconds)

    except KeyboardInterrupt:
        print("\nSymulacja przerwana przez użytkownika.")
    finally:
        # 4. Zatrzymanie loggera (zapisanie resztek z bufora, zamknięcie pliku)
        logger.stop()
        print("Logger zatrzymany. Symulacja zakończona.")

    # 5. Przykład odczytu logów
    print("\n--- Odczytywanie logów ---")
    time_now = datetime.datetime.now()
    start_read_range = time_now - datetime.timedelta(minutes=10)
    end_read_range = time_now

    print(f"Odczyty dla czujnika '{temp_sensor.sensor_id}' z zakresu: {start_read_range} - {end_read_range}")
    try:
        log_entries = logger.read_logs(start_dt=start_read_range, end_dt=end_read_range,
                                       sensor_id=temp_sensor.sensor_id)
        found_any = False
        for entry in log_entries:
            print(f"  {entry['timestamp']} | {entry['sensor_id']} | {entry['value']:.2f} {entry['unit']}")
            found_any = True
        if not found_any:
            print("  Brak logów spełniających kryteria.")
    except Exception as e:
        print(f"Błąd podczas odczytu logów: {e}")

    print(f"\nWszystkie logi z zakresu: {start_read_range} - {end_read_range}")
    try:
        all_log_entries = logger.read_logs(start_dt=start_read_range, end_dt=end_read_range)
        found_any_all = False
        for entry in all_log_entries:
            print(f"  {entry['timestamp']} | {entry['sensor_id']} | {entry['value']:.2f} {entry['unit']}")
            found_any_all = True
        if not found_any_all:
            print("  Brak logów w podanym zakresie.")
    except Exception as e:
        print(f"Błąd podczas odczytu wszystkich logów: {e}")