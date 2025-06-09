import time
import datetime
from typing import List

# Importy modułów z projektu
from sensor import TemperatureSensor, HumiditySensor, PressureSensor, LightSensor, sensor as BaseSensor
from Logger import Logger
import threading
from network.client import NetworkClient
from server.server import NetworkServer
from network.config import load_client_config


class SensorApplication:
    def __init__(self):
        # Inicjalizacja Loggera
        self.logger = Logger(config_path='config.json')
        self.logger.start()

        # self.server = NetworkServer(
        #     host='127.0.0.1',
        #     port=9999,
        # )
        # self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        # self.server_thread.start()

        # Inicjalizacja klienta sieciowego
        client_config = load_client_config()
        self.network_client = NetworkClient(
            host=client_config['host'],
            port=client_config['port'],
            timeout=client_config['timeout'],
            retries=client_config['retries']
        )

        # Inicjalizacja sensorów
        self.sensors: List[BaseSensor] = [
            TemperatureSensor(sensor_id="temp_01", name="Czujnik temperatury", unit="°C", min_value=-20, max_value=40,
                              frequency=5),
            HumiditySensor(sensor_id="hum_01", name="Czujnik wilgotności", unit="%", min_value=0, max_value=100,
                           frequency=7),
            PressureSensor(sensor_id="press_01", name="Czujnik ciśnienia", unit="hPa", min_value=950, max_value=1050,
                           frequency=10),
            LightSensor(sensor_id="light_01", name="Czujnik światła", unit="lux", min_value=0, max_value=2000,
                        frequency=6),
        ]

    def process_sensor_reading(self, sensor_id: str, timestamp: datetime.datetime, value: float, unit: str):
        """
        Callback wywoływany przez sensor po nowym odczycie.
        Loguje dane i wysyła je na serwer.
        """
        print(f"Nowy odczyt z {sensor_id}: {value:.2f} {unit}")

        # 1. Logowanie danych do pliku CSV za pomocą Loggera
        self.logger.log_reading(sensor_id, timestamp, round(value, 2), unit)

        # 2. Przygotowanie i wysłanie danych na serwer
        data_packet = {
            "sensor_id": sensor_id,
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2),
            "unit": unit
        }

        if not self.network_client.send(data_packet):
            print(f"BŁĄD: Nie udało się wysłać danych z sensora {sensor_id} na serwer.")

    def run(self):
        """
        Główna pętla aplikacji.
        """
        print("Uruchamianie aplikacji sensorów...")
        try:
            self.network_client.connect()

            # Pętla symulująca działanie
            while True:
                for s in self.sensors:
                    # Metoda read_value symuluje odczyt i uwzględnia częstotliwość
                    # Dla uproszczenia, będziemy tu bezpośrednio wywoływać odczyt,
                    # a metoda sama zdecyduje, czy wygenerować nową wartość.
                    old_value = s.last_value
                    new_value = s.read_value()

                    # Wywołaj callback tylko, jeśli wartość jest nowa
                    if new_value != old_value:
                        self.process_sensor_reading(s.sensor_id, s._last_read_time, new_value, s.unit)

                time.sleep(1)  # Sprawdzaj sensory co sekundę

        except ConnectionRefusedError:
            print("Nie można połączyć się z serwerem. Sprawdź, czy jest uruchomiony.")
        except KeyboardInterrupt:
            print("\nZamykanie aplikacji...")
        finally:
            self.logger.stop()
            self.network_client.close()
            print("Aplikacja została zatrzymana.")


if __name__ == "__main__":
    app = SensorApplication()
    app.run()