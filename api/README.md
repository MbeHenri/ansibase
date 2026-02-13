# Ansibase API

API REST pour la gestion d'inventaire Ansible dynamique avec PostgreSQL. Gere les hotes, groupes, variables et l'export d'inventaire au format Ansible.

## Prerequis

- **Python** 3.12+
- **PostgreSQL** 12+ avec l'extension `pgcrypto`

## Installation

```bash
pip install -r requirements.txt
```

### Configuration

Copier le fichier d'exemple et l'adapter :

```bash
cp .env.example .env
```

Variables d'environnement :

| Variable                  | Description                                 | Defaut      |
| ------------------------- | ------------------------------------------- | ----------- |
| `ANSIBASE_DB_HOST`        | Hote PostgreSQL                             | `localhost` |
| `ANSIBASE_DB_PORT`        | Port PostgreSQL                             | `5432`      |
| `ANSIBASE_DB_NAME`        | Nom de la base                              | `ansibase`  |
| `ANSIBASE_DB_USER`        | Utilisateur PostgreSQL                      | `ansibase`  |
| `ANSIBASE_DB_PASSWORD`    | Mot de passe PostgreSQL                     | `ansibase`  |
| `ANSIBLE_ENCRYPTION_KEY`  | Cle de chiffrement pgcrypto (obligatoire)   | —           |
| `ANSIBASE_SECRET_KEY`     | Cle secrete de l'application (obligatoire)  | —           |
| `ANSIBASE_ADMIN_USERNAME` | Nom de l'administrateur par defaut          | `admin`     |
| `ANSIBASE_ADMIN_PASSWORD` | Mot de passe de l'administrateur par defaut | `admin`     |

> Generer la cle secrete : `python -c "import secrets; print(secrets.token_hex(32))"`

## Demarrage

### Avec Docker Compose (depuis la racine du projet)

```bash
cp .env.example ../.env
docker compose up --build
```

Les migrations Alembic sont appliquees automatiquement au demarrage.

### En local

```bash
# Appliquer les migrations
python3 manage-db.py upgrade head

# Lancer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentation interactive :

- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`

## Authentification

Tous les endpoints (sauf `POST /api/v1/auth/login` et `GET /`) necessitent un token Bearer (cle API).

```bash
# Se connecter pour obtenir une cle API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Utiliser la cle API retournee
curl -H "Authorization: Bearer <api_key>" http://localhost:8000/api/v1/hosts
```

## Endpoints

### Health

| Methode | Endpoint | Description   |
| ------- | -------- | ------------- |
| `GET`   | `/`      | Etat de l'API |

### Auth

| Methode | Endpoint             | Description                                        |
| ------- | -------------------- | -------------------------------------------------- |
| `POST`  | `/api/v1/auth/login` | Connexion (username/password), retourne la cle API |

### Users (superuser)

| Methode  | Endpoint                               | Description              |
| -------- | -------------------------------------- | ------------------------ |
| `POST`   | `/api/v1/users`                        | Creer un utilisateur     |
| `GET`    | `/api/v1/users`                        | Lister les utilisateurs  |
| `GET`    | `/api/v1/users/{id}`                   | Recuperer un utilisateur |
| `PUT`    | `/api/v1/users/{id}`                   | Modifier un utilisateur  |
| `DELETE` | `/api/v1/users/{id}`                   | Supprimer un utilisateur |
| `POST`   | `/api/v1/users/{id}/api-keys`          | Creer une cle API        |
| `GET`    | `/api/v1/users/{id}/api-keys`          | Lister les cles API      |
| `DELETE` | `/api/v1/users/{id}/api-keys/{key_id}` | Revoquer une cle API     |

### Hosts

| Methode  | Endpoint                                | Description                                                 |
| -------- | --------------------------------------- | ----------------------------------------------------------- |
| `POST`   | `/api/v1/hosts`                         | Creer un hote                                               |
| `GET`    | `/api/v1/hosts`                         | Lister les hotes (filtres : `is_active`, `group`, `search`) |
| `GET`    | `/api/v1/hosts/{id}`                    | Recuperer un hote                                           |
| `PUT`    | `/api/v1/hosts/{id}`                    | Modifier un hote                                            |
| `DELETE` | `/api/v1/hosts/{id}`                    | Supprimer un hote                                           |
| `POST`   | `/api/v1/hosts/{id}/groups`             | Ajouter a un groupe                                         |
| `GET`    | `/api/v1/hosts/{id}/groups`             | Lister les groupes                                          |
| `DELETE` | `/api/v1/hosts/{id}/groups/{group_id}`  | Retirer d'un groupe                                         |
| `POST`   | `/api/v1/hosts/{id}/variables`          | Assigner une variable                                       |
| `GET`    | `/api/v1/hosts/{id}/variables`          | Lister les variables (`?reveal=true` pour les sensibles)    |
| `PUT`    | `/api/v1/hosts/{id}/variables`          | Assigner des variables en masse                             |
| `PUT`    | `/api/v1/hosts/{id}/variables/{var_id}` | Modifier une variable                                       |
| `DELETE` | `/api/v1/hosts/{id}/variables/{var_id}` | Retirer une variable                                        |

### Groups

| Methode  | Endpoint                                          | Description                                           |
| -------- | ------------------------------------------------- | ----------------------------------------------------- |
| `POST`   | `/api/v1/groups`                                  | Creer un groupe                                       |
| `GET`    | `/api/v1/groups`                                  | Lister les groupes (`?tree=true` pour l'arborescence) |
| `GET`    | `/api/v1/groups/{id}`                             | Recuperer un groupe                                   |
| `PUT`    | `/api/v1/groups/{id}`                             | Modifier un groupe                                    |
| `DELETE` | `/api/v1/groups/{id}`                             | Supprimer un groupe                                   |
| `GET`    | `/api/v1/groups/{id}/hosts`                       | Lister les hotes (`?inherited=true`)                  |
| `POST`   | `/api/v1/groups/{id}/variables`                   | Assigner une variable                                 |
| `GET`    | `/api/v1/groups/{id}/variables`                   | Lister les variables (`?inherited=true`)              |
| `PUT`    | `/api/v1/groups/{id}/variables`                   | Assigner des variables en masse                       |
| `PUT`    | `/api/v1/groups/{id}/variables/{var_id}`          | Modifier une variable                                 |
| `DELETE` | `/api/v1/groups/{id}/variables/{var_id}`          | Retirer une variable                                  |
| `POST`   | `/api/v1/groups/{id}/required-variables`          | Definir une variable requise                          |
| `GET`    | `/api/v1/groups/{id}/required-variables`          | Lister les variables requises                         |
| `DELETE` | `/api/v1/groups/{id}/required-variables/{var_id}` | Retirer une variable requise                          |

### Variables

| Methode  | Endpoint                              | Description                                                                      |
| -------- | ------------------------------------- | -------------------------------------------------------------------------------- |
| `POST`   | `/api/v1/variables`                   | Creer une variable                                                               |
| `GET`    | `/api/v1/variables`                   | Lister le catalogue (filtres : `is_sensitive`, `is_ansible_builtin`, `var_type`) |
| `GET`    | `/api/v1/variables/{id}`              | Recuperer une variable                                                           |
| `PUT`    | `/api/v1/variables/{id}`              | Modifier une variable                                                            |
| `DELETE` | `/api/v1/variables/{id}`              | Supprimer une variable (`?force=true` pour les builtins)                         |
| `POST`   | `/api/v1/variables/{id}/aliases`      | Creer un alias                                                                   |
| `GET`    | `/api/v1/variables/{id}/aliases`      | Lister les alias                                                                 |
| `DELETE` | `/api/v1/variable-aliases/{alias_id}` | Supprimer un alias                                                               |

### Inventory

| Methode | Endpoint                             | Description                                         |
| ------- | ------------------------------------ | --------------------------------------------------- |
| `GET`   | `/api/v1/inventory`                  | Exporter l'inventaire complet (format Ansible JSON) |
| `GET`   | `/api/v1/inventory/hosts/{hostname}` | Variables d'un hote specifique                      |
| `GET`   | `/api/v1/inventory/graph`            | Arborescence des groupes                            |

### Audit (superuser)

| Methode | Endpoint             | Description                                                                               |
| ------- | -------------------- | ----------------------------------------------------------------------------------------- |
| `GET`   | `/api/v1/audit-logs` | Journaux d'audit (filtres : `user_id`, `action`, `resource_type`, `date_from`, `date_to`) |

> Les identifiants `{id}` acceptent un ID numerique ou un nom (hostname, group name, var_key, username).
> Les endpoints de listing supportent la pagination : `?page=1&per_page=50`

## Exemples

**Creer un hote :**

```bash
curl -X POST http://localhost:8000/api/v1/hosts \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "web01.example.com", "description": "Serveur web principal"}'
```

**Ajouter un hote a un groupe :**

```bash
curl -X POST http://localhost:8000/api/v1/hosts/web01.example.com/groups \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"group_id_or_name": "webservers"}'
```

**Assigner une variable a un hote :**

```bash
curl -X POST http://localhost:8000/api/v1/hosts/web01.example.com/variables \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"var_id_or_key": "ansible_host", "value": "192.168.1.10"}'
```

**Exporter l'inventaire complet :**

```bash
curl -H "Authorization: Bearer <api_key>" http://localhost:8000/api/v1/inventory
```

**Groupes en arborescence :**

```bash
curl -H "Authorization: Bearer <api_key>" "http://localhost:8000/api/v1/groups?tree=true"
```

## Tests

Les tests utilisent la base PostgreSQL reelle avec rollback transactionnel par test (aucune donnee persistee).

```bash
# Prerequis : PostgreSQL avec migrations appliquees + .env configure

# Tous les tests
pytest

# Un fichier
pytest tests/test_hosts.py

# Un test specifique
pytest tests/test_hosts.py::test_create_host -v
```
