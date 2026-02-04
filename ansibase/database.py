"""
Module de gestion de la base de données pour ansibase
Gère les connexions SQLAlchemy
"""

from typing import Dict, Any
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base


class DatabaseConfig:
    """Configuration de la base de données"""

    def __init__(
        self, host: str, port: int, database: str, user: str, password: str
    ) -> None:
        self.host: str = host
        self.port: int = port
        self.database: str = database
        self.user: str = user
        self.password: str = password

    @property
    def connection_string(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "DatabaseConfig":
        return cls(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
        )


class Database:
    """Gestionnaire de connexion à la base de données"""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config: DatabaseConfig = config
        self.engine: Engine = create_engine(
            config.connection_string,
            echo=False,  # Mettre à True pour debug SQL
            pool_pre_ping=True,  # Vérifie la connexion avant utilisation
        )
        self.SessionLocal: sessionmaker[Session] = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def get_session(self) -> Session:
        return self.SessionLocal()

    def close(self) -> None:
        self.engine.dispose()

    def create_tables(self) -> None:
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
