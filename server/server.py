import socket
import json
import sys
import threading
import logging

# Prosta konfiguracja loggera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class NetworkServer:
    """
    Prosty serwer TCP nasłuchujący na przychodzące dane w formacie JSON.
    """

    def __init__(self, host: str, port: int):
        """
        Inicjalizuje serwer na wskazanym hoście i porcie.

        Args:
            host (str): Host, na którym serwer będzie nasłuchiwał.
            port (int): Port nasłuchu.
        """
        self.host = host
        self.port = port
        self.logger = logging.getLogger("NetworkServer")
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self) -> None:
        """Uruchamia nasłuchiwanie na połączenia i obsługę klientów."""
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self.logger.info(f"Serwer nasłuchuje na {self.host}:{self.port}")

        try:
            while True:
                client_socket, addr = self._server_socket.accept()
                self.logger.info(f"Nowe połączenie od {addr}")
                # Uruchomienie obsługi klienta w nowym wątku
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                client_thread.start()
        except KeyboardInterrupt:
            self.logger.info("Serwer jest zamykany.")
        finally:
            self._server_socket.close()

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Odbiera dane, wysyła ACK i wypisuje je na konsolę."""
        buffer = ""
        try:
            with client_socket:
                while True:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break  # Połączenie zamknięte przez klienta

                    buffer += data
                    # Wiadomości są rozdzielane znakiem nowej linii
                    while '\n' in buffer:
                        message, buffer = buffer.split('\n', 1)
                        try:
                            payload = json.loads(message)
                            print("\n--- Otrzymano dane ---")
                            for key, value in payload.items():
                                print(f"  {key}: {value}")
                            print("-----------------------\n")

                            # Wysłanie potwierdzenia ACK
                            client_socket.sendall("ACK\n".encode('utf-8'))

                        except json.JSONDecodeError:
                            error_msg = f"Błąd parsowania JSON: {message}"
                            self.logger.error(error_msg)
                            sys.stderr.write(error_msg + '\n')

        except socket.error as e:
            self.logger.error(f"Błąd komunikacji z klientem: {e}")
        finally:
            self.logger.info(f"Połączenie z klientem zostało zamknięte.")
if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = 9999

    server = NetworkServer(HOST, PORT)
    server.start()