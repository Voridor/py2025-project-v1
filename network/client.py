import socket
import json
import logging
import time
from typing import Dict, Optional
from network.config import load_client_config

# Standardowy logger jest tutaj odpowiedniejszy do logowania stanu operacji sieciowych.
# Logger z pliku jest przeznaczony do zapisu danych z sensorów w formacie CSV.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class NetworkClient:
    """
    Klient sieciowy do wysyłania danych do zdalnego serwera przez TCP.
    """

    def __init__(
            self,
            host: str,
            port: int,
            timeout: float = 5.0,
            retries: int = 3
    ):
        """
        Inicjalizuje klienta sieciowego.

        Args:
            host (str): Adres IP lub nazwa hosta serwera.
            port (int): Port serwera.
            timeout (float): Czas oczekiwania na odpowiedź serwera w sekundach.
            retries (int): Liczba prób ponowienia wysłania danych w razie błędu.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self._socket: Optional[socket.socket] = None
        self.logger = logging.getLogger("NetworkClient")

    def connect(self) -> None:
        """
        Nawiązuje połączenie z serwerem.
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self.logger.info(f"Połączono z serwerem {self.host}:{self.port}")
        except socket.error as e:
            self.logger.error(f"Błąd połączenia: {e}")
            self._socket = None
            raise ConnectionRefusedError(f"Nie można połączyć się z {self.host}:{self.port}")

    def send(self, data: dict) -> bool:
        """
        Wysyła dane do serwera i czeka na potwierdzenie.
        """
        if not self._socket:
            self.logger.error("Brak aktywnego połączenia. Użyj metody connect().")
            return False

        serialized_data = self._serialize(data)

        for attempt in range(self.retries):
            try:
                self._socket.sendall(serialized_data)
                self.logger.info(f"Wysłano pakiet: {data}")

                response = self._socket.recv(1024).decode('utf-8').strip()
                if response == "ACK":
                    self.logger.info("Otrzymano potwierdzenie (ACK) od serwera.")
                    return True
                else:
                    self.logger.warning(f"Otrzymano nieoczekiwaną odpowiedź: {response}")

            except socket.timeout:
                self.logger.error(f"Timeout podczas oczekiwania na ACK (próba {attempt + 1}/{self.retries}).")
            except socket.error as e:
                self.logger.error(f"Błąd sieciowy: {e} (próba {attempt + 1}/{self.retries}).")
                # Próba ponownego połączenia
                try:
                    self.close()
                    self.connect()
                except ConnectionRefusedError:
                    time.sleep(1)

        self.logger.error("Wysłanie danych nie powiodło się po wszystkich próbach.")
        return False

    def close(self) -> None:
        """Zamyka połączenie z serwerem."""
        if self._socket:
            self._socket.close()
            self._socket = None
            self.logger.info("Połączenie z serwerem zostało zamknięte.")

    def _serialize(self, data: dict) -> bytes:
        return (json.dumps(data) + '\n').encode('utf-8')

    def _deserialize(self, raw: bytes) -> dict:
        return json.loads(raw.decode('utf-8'))

if __name__ == "__main__":
    config = load_client_config('../config.yaml')
    HOST = config['host']
    PORT = config['port']

    client = NetworkClient(HOST, PORT)
    try:
        client.connect()
        while True:
            msg = input("Podaj dane do wysłania (lub 'exit' aby zakończyć): ")
            if msg.lower() == "exit":
                break
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                print("Podaj dane w formacie JSON!")
                continue
            client.send(data)
    finally:
        client.close()