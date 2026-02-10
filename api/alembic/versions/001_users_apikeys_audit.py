"""Utilisateurs, API Keys et Audit Logs

Revision ID: 002
Revises: 001

Tables: ansibase_users, ansibase_api_keys, ansibase_audit_logs
Données par défaut: utilisateur admin (via env vars)
"""

import os
from app.utils import generate_key, hash_password
from app.config import settings
from alembic import op

revision = "001_init.api"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ansibase_users ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_users_username ON ansibase_users(username)"
    )

    # ── ansibase_api_keys ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES ansibase_users(id) ON DELETE CASCADE,
            key_hash VARCHAR(255) NOT NULL,
            key_value_encrypted BYTEA NOT NULL,
            key_prefix VARCHAR(16) NOT NULL,
            name VARCHAR(255) NOT NULL,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_api_keys_user ON ansibase_api_keys(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_api_keys_prefix ON ansibase_api_keys(key_prefix)"
    )

    # ── ansibase_audit_logs ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES ansibase_users(id) ON DELETE SET NULL,
            action VARCHAR(50) NOT NULL,
            resource_type VARCHAR(100) NOT NULL,
            resource_id VARCHAR(255),
            details JSONB,
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_audit_logs_user ON ansibase_audit_logs(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_audit_logs_action ON ansibase_audit_logs(action)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_audit_logs_resource ON ansibase_audit_logs(resource_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_audit_logs_created ON ansibase_audit_logs(created_at)"
    )

    # ── Trigger updated_at pour ansibase_users ──
    op.execute("DROP TRIGGER IF EXISTS ansibase_users_updated_at ON ansibase_users")
    op.execute(
        """
        CREATE TRIGGER ansibase_users_updated_at
            BEFORE UPDATE ON ansibase_users
            FOR EACH ROW
            EXECUTE FUNCTION ansibase_update_updated_at_column()
    """
    )

    # ── Utilisateur admin par défaut ──
    admin_username = os.environ.get("ANSIBASE_ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ANSIBASE_ADMIN_PASSWORD", "admin")
    password_hash = hash_password(admin_password)

    op.execute(
        f"""
        INSERT INTO ansibase_users (username, password_hash, is_active, is_superuser)
        VALUES ('{admin_username}', '{password_hash}', TRUE, TRUE)
        ON CONFLICT (username) DO NOTHING
        """
    )

    # ── Clé API par défaut pour l'admin ──
    raw_key, key_hash = generate_key()
    key_prefix = raw_key[:12]

    op.execute(
        f"""
        INSERT INTO ansibase_api_keys (user_id, key_hash, key_value_encrypted, key_prefix, name)
        SELECT id, '{key_hash}', pgp_sym_encrypt('{raw_key}', '{settings.ANSIBASE_SECRET_KEY}'), '{key_prefix}', 'default'
        FROM ansibase_users
        WHERE username = '{admin_username}'
          AND NOT EXISTS (
              SELECT 1 FROM ansibase_api_keys
              WHERE user_id = ansibase_users.id AND name = 'default'
          )
        """
    )

    # on affiche la cle en clair dans les logs de migration (visible une seule fois)
    print(f"\n[ansibase] Clé API par défaut pour '{admin_username}': {raw_key}\n")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ansibase_audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_api_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_users CASCADE")
