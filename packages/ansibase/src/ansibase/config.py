"""Chargement de configuration ansibase (INI et YML)"""

from pathlib import Path
from configparser import ConfigParser
from typing import Any, Dict


def load_config(config_file: str = "ansibase.ini") -> Dict[str, Any]:
    """Charge la configuration depuis un fichier INI ou YML.

    Detection du format par extension :
    - .ini           -> ConfigParser
    - .yml / .yaml   -> PyYAML
    """
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration non trouve: {config_path}")

    ext = config_path.suffix.lower()
    if ext in (".yml", ".yaml"):
        return _load_yaml(config_path)
    else:
        return _load_ini(config_path)


def _load_ini(config_path: Path) -> Dict[str, Any]:
    """Charge un fichier INI."""
    parser = ConfigParser()
    parser.read(config_path)

    return {
        "database": {
            "host": parser.get("database", "host"),
            "port": parser.getint("database", "port"),
            "database": parser.get("database", "database"),
            "user": parser.get("database", "user"),
            "password": parser.get("database", "password"),
        },
        "encryption": {
            "key": parser.get("encryption", "key"),
        },
        "cache": {
            "enabled": parser.getboolean("cache", "enabled", fallback=True),
            "ttl": parser.getint("cache", "ttl", fallback=300),
        },
    }


def _load_yaml(config_path: Path) -> Dict[str, Any]:
    """Charge un fichier YAML."""
    import yaml

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return {
        "database": {
            "host": data.get("host", "localhost"),
            "port": int(data.get("port", 5432)),
            "database": data.get("database", "ansible_inventory"),
            "user": data.get("user", "ansible"),
            "password": data["password"],
        },
        "encryption": {
            "key": data.get("encryption_key", data.get("key", "")),
        },
        "cache": {
            "enabled": data.get("cache_enabled", True),
            "ttl": int(data.get("cache_ttl", 300)),
        },
    }
