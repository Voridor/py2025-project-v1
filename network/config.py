import yaml
from typing import Dict, Any

def load_client_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    Wczytuje konfigurację klienta z pliku YAML.

    Args:
        config_path (str): Ścieżka do pliku config.yaml.

    Returns:
        Słownik z konfiguracją klienta.
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('client', {})