"""Schema de base ansibase

Revision ID: 001
Revises:

Tables: ansibase_groups, ansibase_hosts, ansibase_variables,
        ansibase_variable_aliases, ansibase_host_groups,
        ansibase_host_variables, ansibase_group_variables,
        ansibase_group_required_variables
Triggers: updated_at automatique
Données par défaut: groupes all/ungrouped, variables builtin ansible_*
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extension pgcrypto
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── ansibase_groups ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            parent_id INTEGER REFERENCES ansibase_groups(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_groups_name ON ansibase_groups(name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_groups_parent ON ansibase_groups(parent_id)"
    )

    # ── ansibase_hosts ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_hosts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_hosts_name ON ansibase_hosts(name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_hosts_active ON ansibase_hosts(is_active)"
    )

    # ── ansibase_variables ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_variables (
            id SERIAL PRIMARY KEY,
            var_key VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            is_sensitive BOOLEAN DEFAULT FALSE,
            var_type VARCHAR(50) DEFAULT 'string',
            default_value TEXT,
            validation_regex TEXT,
            is_ansible_builtin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_variables_key ON ansibase_variables(var_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_variables_builtin ON ansibase_variables(is_ansible_builtin)"
    )

    # ── ansibase_variable_aliases ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_variable_aliases (
            id SERIAL PRIMARY KEY,
            alias_var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
            source_var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(alias_var_id, source_var_id),
            CHECK (alias_var_id != source_var_id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_variable_aliases_alias ON ansibase_variable_aliases(alias_var_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_variable_aliases_source ON ansibase_variable_aliases(source_var_id)"
    )

    # ── ansibase_host_groups ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_host_groups (
            id SERIAL PRIMARY KEY,
            host_id INTEGER NOT NULL REFERENCES ansibase_hosts(id) ON DELETE CASCADE,
            group_id INTEGER NOT NULL REFERENCES ansibase_groups(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(host_id, group_id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_host_groups_host ON ansibase_host_groups(host_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_host_groups_group ON ansibase_host_groups(group_id)"
    )

    # ── ansibase_host_variables ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_host_variables (
            id SERIAL PRIMARY KEY,
            host_id INTEGER NOT NULL REFERENCES ansibase_hosts(id) ON DELETE CASCADE,
            var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
            var_value TEXT,
            var_value_encrypted BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(host_id, var_id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_host_variables_host ON ansibase_host_variables(host_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_host_variables_var ON ansibase_host_variables(var_id)"
    )

    # ── ansibase_group_variables ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_group_variables (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES ansibase_groups(id) ON DELETE CASCADE,
            var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
            var_value TEXT,
            var_value_encrypted BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, var_id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_group_variables_group ON ansibase_group_variables(group_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_group_variables_var ON ansibase_group_variables(var_id)"
    )

    # ── ansibase_group_required_variables ──
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ansibase_group_required_variables (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES ansibase_groups(id) ON DELETE CASCADE,
            var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
            is_required BOOLEAN DEFAULT TRUE,
            override_default_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, var_id)
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_group_req_vars_group ON ansibase_group_required_variables(group_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_group_req_vars_var ON ansibase_group_required_variables(var_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ansibase_group_req_vars_required ON ansibase_group_required_variables(is_required)"
    )

    # ── Fonction et triggers updated_at ──
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ansibase_update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """
    )

    for table in [
        "ansibase_groups",
        "ansibase_hosts",
        "ansibase_variables",
        "ansibase_variable_aliases",
        "ansibase_group_required_variables",
        "ansibase_host_variables",
        "ansibase_group_variables",
    ]:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_updated_at ON {table}")
        op.execute(
            f"""
            CREATE TRIGGER {table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION ansibase_update_updated_at_column()
        """
        )

    # ── Données par défaut : groupes ──
    op.execute(
        """
        INSERT INTO ansibase_groups (name, description)
        VALUES ('all', 'Groupe racine contenant tous les hôtes')
        ON CONFLICT (name) DO NOTHING
    """
    )
    op.execute(
        """
        INSERT INTO ansibase_groups (name, description, parent_id)
        VALUES ('ungrouped', 'Hôtes sans groupe spécifique',
                (SELECT id FROM ansibase_groups WHERE name = 'all'))
        ON CONFLICT (name) DO NOTHING
    """
    )

    # ── Données par défaut : variables builtin ansible_* ──
    op.execute(
        """
        INSERT INTO ansibase_variables
            (var_key, description, is_sensitive, var_type, default_value, is_ansible_builtin)
        VALUES
            ('ansible_host', 'Adresse IP ou hostname pour la connexion SSH', FALSE, 'string', NULL, TRUE),
            ('ansible_port', 'Port SSH de connexion', FALSE, 'int', '22', TRUE),
            ('ansible_user', 'Utilisateur de connexion SSH', FALSE, 'string', NULL, TRUE),
            ('ansible_password', 'Mot de passe de connexion SSH', TRUE, 'string', NULL, TRUE),
            ('ansible_become_password', 'Mot de passe pour élévation de privilèges', TRUE, 'string', NULL, TRUE)
        ON CONFLICT (var_key) DO NOTHING
    """
    )

    # ── Données par défaut : variables requises pour le groupe "all" ──
    op.execute(
        """
        INSERT INTO ansibase_group_required_variables (group_id, var_id, is_required)
        SELECT
            (SELECT id FROM ansibase_groups WHERE name = 'all'),
            id,
            CASE
                WHEN var_key IN ('ansible_host', 'ansible_user') THEN TRUE
                ELSE FALSE
            END
        FROM ansibase_variables
        WHERE is_ansible_builtin = TRUE
        ON CONFLICT (group_id, var_id) DO NOTHING
    """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ansibase_group_required_variables CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_group_variables CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_host_variables CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_host_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_variable_aliases CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_variables CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_hosts CASCADE")
    op.execute("DROP TABLE IF EXISTS ansibase_groups CASCADE")
    op.execute("DROP FUNCTION IF EXISTS ansibase_update_updated_at_column() CASCADE")
