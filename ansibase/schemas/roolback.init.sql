-- Début de la transaction
START TRANSACTION;

/* ------------------------------------------------------------
   ROLLBACK MIGRATION ansibase
   - Suppression de toutes les tables, vues, fonctions et extensions
   - Ordre inversé de la création pour respecter les dépendances
   ---------------------------------------------------------------- */

-- ==========================
-- 1) Suppression des vues
-- ==========================
DROP VIEW IF EXISTS ansibase_v_variables_catalog CASCADE;

-- ==========================
-- 2) Suppression des triggers
-- ==========================
DROP TRIGGER IF EXISTS ansibase_group_variables_updated_at ON ansibase_group_variables;
DROP TRIGGER IF EXISTS ansibase_host_variables_updated_at ON ansibase_host_variables;
DROP TRIGGER IF EXISTS ansibase_group_required_variables_updated_at ON ansibase_group_required_variables;
DROP TRIGGER IF EXISTS ansibase_variable_aliases_updated_at ON ansibase_variable_aliases;
DROP TRIGGER IF EXISTS ansibase_variables_updated_at ON ansibase_variables;
DROP TRIGGER IF EXISTS ansibase_hosts_updated_at ON ansibase_hosts;
DROP TRIGGER IF EXISTS ansibase_groups_updated_at ON ansibase_groups;

-- ==========================
-- 3) Suppression de la fonction
-- ==========================
DROP FUNCTION IF EXISTS ansibase_update_updated_at_column() CASCADE;

-- ==========================
-- 4) Suppression des tables (dans l'ordre des dépendances)
-- ==========================
DROP TABLE IF EXISTS ansibase_group_variables CASCADE;
DROP TABLE IF EXISTS ansibase_host_variables CASCADE;
DROP TABLE IF EXISTS ansibase_group_required_variables CASCADE;
DROP TABLE IF EXISTS ansibase_variable_aliases CASCADE;
DROP TABLE IF EXISTS ansibase_variables CASCADE;
DROP TABLE IF EXISTS ansibase_host_groups CASCADE;
DROP TABLE IF EXISTS ansibase_hosts CASCADE;
DROP TABLE IF EXISTS ansibase_groups CASCADE;

-- ==========================
-- 5) Suppression de l'extension pgcrypto (optionnel)
-- ==========================
-- Décommentez la ligne suivante si vous voulez supprimer l'extension
-- Attention : cela affectera d'autres tables/fonctions qui l'utilisent
-- DROP EXTENSION IF EXISTS pgcrypto CASCADE;

-- Si tout est OK
COMMIT;