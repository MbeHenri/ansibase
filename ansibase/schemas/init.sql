-- Début de la transaction
START TRANSACTION;

/* ------------------------------------------------------------
   MIGRATION TABLE ansibase
   - Création du schéma pour la gestion d'inventaire Ansible
   - Tables: hosts, groups, host_groups, host_variables, group_variables, group_required_variables, variable_aliases, variables
   - Support du chiffrement pour données sensibles
   - Support des alias de variables
   - Variables utiles définies indépendamment des groupes (ansible_*)
   ---------------------------------------------------------------- */

-- ==========================
-- 1) Création de l'extension pour le chiffrement
-- ==========================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ==========================
-- 2) Création de la table ansibase_groups
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER REFERENCES ansibase_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ansibase_groups_name ON ansibase_groups(name);
CREATE INDEX idx_ansibase_groups_parent ON ansibase_groups(parent_id);

COMMENT ON TABLE ansibase_groups IS 'Groupes d''hôtes Ansible';
COMMENT ON COLUMN ansibase_groups.parent_id IS 'Permet la hiérarchie de groupes (children)';

-- ==========================
-- 3) Création de la table ansibase_hosts
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_hosts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ansibase_hosts_name ON ansibase_hosts(name);
CREATE INDEX idx_ansibase_hosts_active ON ansibase_hosts(is_active);

COMMENT ON TABLE ansibase_hosts IS 'Hôtes de l''inventaire Ansible';
COMMENT ON COLUMN ansibase_hosts.name IS 'Nom unique de l''hôte dans l''inventaire';
COMMENT ON COLUMN ansibase_hosts.is_active IS 'Permet de désactiver un hôte sans le supprimer';

-- ==========================
-- 4) Création de la table ansibase_host_groups
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_host_groups (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES ansibase_hosts(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES ansibase_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, group_id)
);

CREATE INDEX idx_ansibase_host_groups_host ON ansibase_host_groups(host_id);
CREATE INDEX idx_ansibase_host_groups_group ON ansibase_host_groups(group_id);

COMMENT ON TABLE ansibase_host_groups IS 'Relation many-to-many entre hosts et groups';

-- ==========================
-- 5) Création de la table ansibase_variables
-- ==========================
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
);

CREATE INDEX idx_ansibase_variables_key ON ansibase_variables(var_key);
CREATE INDEX idx_ansibase_variables_builtin ON ansibase_variables(is_ansible_builtin);

COMMENT ON TABLE ansibase_variables IS 'Catalogue de toutes les variables disponibles (ansible_*, site_*, custom, etc.)';
COMMENT ON COLUMN ansibase_variables.var_key IS 'Nom de la variable';
COMMENT ON COLUMN ansibase_variables.is_sensitive IS 'Indique si la variable contient des données sensibles';
COMMENT ON COLUMN ansibase_variables.var_type IS 'Type de la variable: string, int, bool, list, dict';
COMMENT ON COLUMN ansibase_variables.default_value IS 'Valeur par défaut globale';
COMMENT ON COLUMN ansibase_variables.validation_regex IS 'Expression régulière pour valider la valeur';
COMMENT ON COLUMN ansibase_variables.is_ansible_builtin IS 'TRUE si c''est une variable Ansible native (ansible_*)';

-- ==========================
-- 6) Création de la table ansibase_variable_aliases
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_variable_aliases (
    id SERIAL PRIMARY KEY,
    alias_var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
    source_var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alias_var_id, source_var_id),
    CHECK (alias_var_id != source_var_id)
);

CREATE INDEX idx_ansibase_variable_aliases_alias ON ansibase_variable_aliases(alias_var_id);
CREATE INDEX idx_ansibase_variable_aliases_source ON ansibase_variable_aliases(source_var_id);

COMMENT ON TABLE ansibase_variable_aliases IS 'Définition des alias de variables (ex: ansible_host est un alias de site_host)';
COMMENT ON COLUMN ansibase_variable_aliases.alias_var_id IS 'ID de la variable alias';
COMMENT ON COLUMN ansibase_variable_aliases.source_var_id IS 'ID de la variable source';

-- ==========================
-- 7) Création de la table ansibase_group_required_variables
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_group_required_variables (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES ansibase_groups(id) ON DELETE CASCADE,
    var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT TRUE,
    override_default_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, var_id)
);

CREATE INDEX idx_ansibase_group_req_vars_group ON ansibase_group_required_variables(group_id);
CREATE INDEX idx_ansibase_group_req_vars_var ON ansibase_group_required_variables(var_id);
CREATE INDEX idx_ansibase_group_req_vars_required ON ansibase_group_required_variables(is_required);

COMMENT ON TABLE ansibase_group_required_variables IS 'Association entre groupes et variables (requises ou optionnelles)';
COMMENT ON COLUMN ansibase_group_required_variables.var_id IS 'ID de la variable définie';
COMMENT ON COLUMN ansibase_group_required_variables.is_required IS 'Si TRUE, la variable doit être définie pour chaque hôte du groupe';
COMMENT ON COLUMN ansibase_group_required_variables.override_default_value IS 'Permet de surcharger la valeur par défaut pour ce groupe';

-- ==========================
-- 8) Création de la table ansibase_host_variables
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_host_variables (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES ansibase_hosts(id) ON DELETE CASCADE,
    var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
    var_value TEXT,
    var_value_encrypted BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, var_id)
);

CREATE INDEX idx_ansibase_host_variables_host ON ansibase_host_variables(host_id);
CREATE INDEX idx_ansibase_host_variables_var ON ansibase_host_variables(var_id);

COMMENT ON TABLE ansibase_host_variables IS 'Variables spécifiques aux hôtes (host_vars)';
COMMENT ON COLUMN ansibase_host_variables.var_value IS 'Valeur en clair pour variables non sensibles';
COMMENT ON COLUMN ansibase_host_variables.var_value_encrypted IS 'Valeur chiffrée pour variables sensibles';

-- ==========================
-- 9) Création de la table ansibase_group_variables
-- ==========================
CREATE TABLE IF NOT EXISTS ansibase_group_variables (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES ansibase_groups(id) ON DELETE CASCADE,
    var_id INTEGER NOT NULL REFERENCES ansibase_variables(id) ON DELETE CASCADE,
    var_value TEXT,
    var_value_encrypted BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, var_id)
);

CREATE INDEX idx_ansibase_group_variables_group ON ansibase_group_variables(group_id);
CREATE INDEX idx_ansibase_group_variables_var ON ansibase_group_variables(var_id);

COMMENT ON TABLE ansibase_group_variables IS 'Variables spécifiques aux groupes (group_vars)';
COMMENT ON COLUMN ansibase_group_variables.var_value IS 'Valeur en clair pour variables non sensibles';
COMMENT ON COLUMN ansibase_group_variables.var_value_encrypted IS 'Valeur chiffrée pour variables sensibles';

-- ==========================
-- 10) Création de la fonction de mise à jour du timestamp
-- ==========================
CREATE OR REPLACE FUNCTION ansibase_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==========================
-- 11) Création des triggers pour updated_at
-- ==========================
CREATE TRIGGER ansibase_groups_updated_at
    BEFORE UPDATE ON ansibase_groups
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

CREATE TRIGGER ansibase_hosts_updated_at
    BEFORE UPDATE ON ansibase_hosts
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

CREATE TRIGGER ansibase_variables_updated_at
    BEFORE UPDATE ON ansibase_variables
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

CREATE TRIGGER ansibase_variable_aliases_updated_at
    BEFORE UPDATE ON ansibase_variable_aliases
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

CREATE TRIGGER ansibase_group_required_variables_updated_at
    BEFORE UPDATE ON ansibase_group_required_variables
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

CREATE TRIGGER ansibase_host_variables_updated_at
    BEFORE UPDATE ON ansibase_host_variables
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

CREATE TRIGGER ansibase_group_variables_updated_at
    BEFORE UPDATE ON ansibase_group_variables
    FOR EACH ROW
    EXECUTE FUNCTION ansibase_update_updated_at_column();

-- ==========================
-- 12) Création de vues utiles
-- ==========================

-- Vue pour lister toutes les variables disponibles avec leurs alias
CREATE OR REPLACE VIEW ansibase_v_variables_catalog AS
SELECT 
    vd.id,
    vd.var_key,
    vd.description,
    vd.is_sensitive,
    vd.var_type,
    vd.default_value,
    vd.is_ansible_builtin,
    COALESCE(
        json_agg(
            json_build_object(
                'alias_key', vd_alias.var_key,
                'description', va.description
            )
        ) FILTER (WHERE vd_alias.id IS NOT NULL),
        '[]'::json
    ) AS aliases,
    COALESCE(
        json_agg(
            json_build_object(
                'source_key', vd_source.var_key,
                'description', va_source.description
            )
        ) FILTER (WHERE vd_source.id IS NOT NULL),
        '[]'::json
    ) AS alias_of
FROM ansibase_variables vd
LEFT JOIN ansibase_variable_aliases va ON vd.id = va.source_var_id
LEFT JOIN ansibase_variables vd_alias ON va.alias_var_id = vd_alias.id
LEFT JOIN ansibase_variable_aliases va_source ON vd.id = va_source.alias_var_id
LEFT JOIN ansibase_variables vd_source ON va_source.source_var_id = vd_source.id
GROUP BY vd.id, vd.var_key, vd.description, vd.is_sensitive, vd.var_type, vd.default_value, vd.is_ansible_builtin;

COMMENT ON VIEW ansibase_v_variables_catalog IS 'Vue affichant les variables avec leurs alias';


-- ==========================
-- 13) Insertion de données par défaut
-- ==========================

-- Groupe "all" par défaut (requis par Ansible)
INSERT INTO ansibase_groups (name, description) 
VALUES ('all', 'Groupe racine contenant tous les hôtes')
ON CONFLICT (name) DO NOTHING;

-- Groupe "ungrouped" par défaut
INSERT INTO ansibase_groups (name, description, parent_id) 
VALUES ('ungrouped', 'Hôtes sans groupe spécifique', (SELECT id FROM ansibase_groups WHERE name = 'all'))
ON CONFLICT (name) DO NOTHING;

-- ==========================
-- 14) Définition des variables Ansible standards (builtin)
-- ==========================

INSERT INTO ansibase_variables 
    (var_key, description, is_sensitive, var_type, default_value, is_ansible_builtin)
VALUES 
    ('ansible_host', 'Adresse IP ou hostname pour la connexion SSH', FALSE, 'string', NULL, TRUE),
    ('ansible_port', 'Port SSH de connexion', FALSE, 'int', '22', TRUE),
    ('ansible_user', 'Utilisateur de connexion SSH', FALSE, 'string', NULL, TRUE),
    ('ansible_password', 'Mot de passe de connexion SSH', TRUE, 'string', NULL, TRUE),
    ('ansible_become_password', 'Mot de passe pour élévation de privilèges', TRUE, 'string', NULL, TRUE);

-- ==========================
-- 15) Association des variables Ansible au groupe "all"
-- ==========================

-- Rendre certaines variables Ansible requises pour tous les hôtes
INSERT INTO ansibase_group_required_variables (group_id, var_id, is_required)
SELECT 
    (SELECT id FROM ansibase_groups WHERE name = 'all'),
    id,
    CASE 
        WHEN var_key IN ('ansible_host', 'ansible_user') THEN TRUE
        ELSE FALSE
    END
FROM ansibase_variables
WHERE is_ansible_builtin = TRUE;

-- Si tout est OK
COMMIT;