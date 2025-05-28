class NetworkClient:
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 5.0,
        retries: int = 3
    ):
        """Inicjalizuje klienta sieciowego."""

    def connect(self) -> None:
        """Nawiazuje połączenie z serwerem."""

    def send(self, data: dict) -> bool:
        """Wysyła dane i czeka na potwierdzenie zwrotne."""

    def close(self) -> None:
        """Zamyka połączenie."""

    # Metody pomocnicze:
    def _serialize(self, data: dict) -> bytes:
        pass

    def _deserialize(self, raw: bytes) -> dict:
        pass