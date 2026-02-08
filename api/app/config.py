"""
Configuration de l'application via variables d'environnement
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration centralisée de l'API ansibase"""

    # Base de données
    ANSIBASE_DB_HOST: str = "localhost"
    ANSIBASE_DB_PORT: int = 5432
    ANSIBASE_DB_NAME: str = "ansibase"
    ANSIBASE_DB_USER: str = "ansibase"
    ANSIBASE_DB_PASSWORD: str = "ansibase"

    # Chiffrement des variables sensibles d'ansible (obligatoire, pas de valeur par défaut)
    ANSIBLE_ENCRYPTION_KEY: str

    # Clé secrète d'ansibase (obligatoire)
    # Générer avec : python -c "import secrets; print(secrets.token_hex(32))"
    ANSIBASE_SECRET_KEY: str

    # Utilisateur admin par défaut
    ANSIBASE_ADMIN_USERNAME: str = "admin"
    ANSIBASE_ADMIN_PASSWORD: str = "admin"

    # API
    ANSIBASE_API_TITLE: str = "Ansibase API"
    ANSIBASE_API_VERSION: str = "1.0.0"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.ANSIBASE_DB_USER}:{self.ANSIBASE_DB_PASSWORD}"
            f"@{self.ANSIBASE_DB_HOST}:{self.ANSIBASE_DB_PORT}/{self.ANSIBASE_DB_NAME}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
