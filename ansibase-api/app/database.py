"""
Gestion de la connexion base de données pour l'API
Fournit le moteur SQLAlchemy et la dépendance get_db pour FastAPI
"""

from typing import Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from .config import settings

# moteur de sqlachemy pour l'acces a la BD
engine: Engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# recuperation d'un marqueur globale de session pour la connection a la base de donnees
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : fournit une session DB avec commit/rollback automatique"""
    
    # on recupere la session
    db = SessionLocal()
    try:
        # on retourne la session
        yield db
        # a la prochaine execution on commit les modifications
        db.commit()
    except Exception:
        # s'il y'a une erreur on les annule
        db.rollback()
        raise
    finally:
        # on ferme la connexion par la suite
        db.close()
