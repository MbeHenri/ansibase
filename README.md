# ansibase

Systeme d'inventaire dynamique pour Ansible adosse a PostgreSQL, avec une API REST pour la gestion centralisee des hotes, groupes, variables et leurs relations. Supporte le chiffrement des variables sensibles via pgcrypto et l'aliasing de variables.

Deux modes d'integration avec Ansible sont disponibles :

- **Mode plugin** : plugin d'inventaire Ansible (`ansibase_ansible`)
- **Mode script** : commande `ansibase-inventory`

## Structure du projet

```txt
.
├── packages/ansibase/                # package Python core (inventaire)
│   ├── pyproject.toml
│   └── src/ansibase/
│       ├── __init__.py
│       ├── builder.py                  # construction de l'inventaire Ansible
│       ├── crypto.py                   # chiffrement/dechiffrement via pgcrypto
│       ├── database.py                 # connexion et gestion de la base de donnees
│       ├── graph.py                    # arborescence hierarchique des groupes
│       ├── models/                     # modeles ORM (SQLAlchemy)
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── group.py
│       │   ├── host.py
│       │   └── variable.py
│       ├── ansible/                    # integration Ansible (plugin + script)
│       │   ├── __init__.py
│       │   ├── ansibase_ansible.py
│       │   └── inventory.py
│       └── schemas/                    # schemas SQL
│           ├── init.sql
│           └── roolback.init.sql
├── api/                              # API REST (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # point d'entree FastAPI
│   │   ├── config.py                   # configuration (variables d'environnement)
│   │   ├── database.py                 # session SQLAlchemy
│   │   ├── utils.py
│   │   ├── models/                     # modeles User, ApiKey, AuditLog
│   │   ├── routers/                    # endpoints HTTP
│   │   ├── schemas/                    # modeles Pydantic
│   │   ├── services/                   # logique metier
│   │   └── dependencies/              # auth, pagination, resolution
│   ├── alembic/                        # migrations de base de donnees
│   │   └── versions/
│   │       ├── 001_schema_base.py
│   │       └── 002_users_apikeys_audit.py
│   └── tests/                          # tests API (pytest)
├── docker-compose.yml                # Docker Compose (PostgreSQL + API)
├── ansible.cfg                       # configuration Ansible
├── example.ansibase.yml              # configuration d'exemple (mode plugin)
├── example.ansibase.ini              # configuration d'exemple (mode script)
├── docs/                             # images de documentation
│   ├── ansibase_using.png
│   └── hosts_bd.png
├── requirements.txt                  # dependances completes (avec Ansible)
└── LICENSE                           # GPL-3.0
```

## Prerequis

- **Python** 3.12+
- **PostgreSQL** 12+ avec l'extension `pgcrypto`
- **Ansible** 2.18+ (`ansible-core`) — optionnel, uniquement pour l'integration Ansible

## Installation

### 1. Cloner le depot

```bash
git clone https://github.com/MbeHenri/ansibase.git
cd ansibase
```

### 2. Creer un environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer le package core

```bash
pip install -e packages/ansibase
```

Pour inclure le support Ansible (plugin et script d'inventaire) :

```bash
pip install -e "packages/ansibase[ansible]"
```

### 4. Installer l'API

```bash
pip install -r api/requirements.txt
```

### 5. Configurer l'environnement

Copier le fichier d'exemple et l'adapter :

```bash
cp api/.env.example api/.env
```

Editer `api/.env` avec les vrais parametres :

```env
ANSIBASE_DB_HOST=localhost
ANSIBASE_DB_PORT=5432
ANSIBASE_DB_NAME=ansibase
ANSIBASE_DB_USER=ansibase
ANSIBASE_DB_PASSWORD=ansibase

ANSIBLE_ENCRYPTION_KEY=votre_cle_de_chiffrement
ANSIBASE_SECRET_KEY=votre_cle_secrete    # python -c "import secrets; print(secrets.token_hex(32))"

ANSIBASE_ADMIN_USERNAME=admin
ANSIBASE_ADMIN_PASSWORD=admin
```

Pour le mode plugin Ansible, copier egalement :

```bash
cp example.ansibase.yml ansibase.yml
# Editer ansibase.yml avec les parametres de connexion
```

## Demarrage avec Docker

Le moyen le plus rapide pour lancer l'ensemble (PostgreSQL + API) :

```bash
cp api/.env.example api/.env
# Editer api/.env avec vos parametres

docker compose up --build
```

L'API est accessible sur `http://localhost:8000` et la base de donnees sur le port `5432`.

Les migrations Alembic sont appliquees automatiquement au demarrage du conteneur API.

## Demarrage local

### 1. Creer la base de donnees PostgreSQL

```bash
sudo -u postgres createuser --pwprompt ansibase
sudo -u postgres createdb -O ansibase ansibase
```

### 2. Appliquer les migrations

```bash
cd api
alembic upgrade head
cd ..
```

### 3. Lancer l'API

```bash
cd api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API est accessible sur `http://localhost:8000`.

## API REST

Documentation interactive disponible sur :

- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`

### Authentification

Tous les endpoints (sauf `/api/v1/auth/login` et `GET /`) necessitent un token Bearer (cle API).

```bash
# Se connecter pour obtenir une cle API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Utiliser la cle API retournee dans les requetes suivantes :

```bash
curl -H "Authorization: Bearer <api_key>" http://localhost:8000/api/v1/hosts
```

### Endpoints principaux

| Ressource   | Methode | Endpoint | Description |
|-------------|---------|----------|-------------|
| Health      | `GET`   | `/` | Etat de l'API |
| **Auth**    | `POST`  | `/api/v1/auth/login` | Connexion (username/password) |
| **Users**   | `CRUD`  | `/api/v1/users` | Gestion des utilisateurs |
|             | `CRUD`  | `/api/v1/users/{id}/api-keys` | Gestion des cles API |
| **Hosts**   | `CRUD`  | `/api/v1/hosts` | Gestion des hotes |
|             | `CRUD`  | `/api/v1/hosts/{id}/groups` | Groupes d'un hote |
|             | `CRUD`  | `/api/v1/hosts/{id}/variables` | Variables d'un hote |
| **Groups**  | `CRUD`  | `/api/v1/groups` | Gestion des groupes |
|             | `CRUD`  | `/api/v1/groups/{id}/variables` | Variables d'un groupe |
|             | `CRUD`  | `/api/v1/groups/{id}/required-variables` | Variables requises |
|             | `GET`   | `/api/v1/groups/{id}/hosts` | Hotes d'un groupe |
| **Variables** | `CRUD` | `/api/v1/variables` | Catalogue de variables |
|             | `CRUD`  | `/api/v1/variables/{id}/aliases` | Alias de variables |
| **Inventory** | `GET` | `/api/v1/inventory` | Export inventaire (format Ansible JSON) |
|             | `GET`   | `/api/v1/inventory/hosts/{hostname}` | Variables d'un hote |
|             | `GET`   | `/api/v1/inventory/graph` | Arborescence des groupes |
| **Audit**   | `GET`   | `/api/v1/audit-logs` | Journaux d'audit (superuser) |

> Les identifiants (`{id}`) acceptent aussi bien un ID numerique qu'un nom (hostname, group name, var_key, username).

> Les endpoints de listing supportent la pagination : `?page=1&per_page=50`

### Exemples curl

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

**Recuperer les groupes sous forme d'arbre :**

```bash
curl -H "Authorization: Bearer <api_key>" "http://localhost:8000/api/v1/groups?tree=true"
```

## Integration Ansible

### Mode plugin (`ansibase_ansible`)

Le plugin s'integre nativement dans le systeme de plugins d'Ansible. Il necessite un fichier de configuration YAML (`ansibase.yml`) et que le plugin soit active dans `ansible.cfg`.

**Configuration de `ansible.cfg`** (deja fourni dans le depot) :

```ini
[defaults]
inventory_plugins = packages/ansibase/src/ansibase/ansible

[inventory]
enable_plugins = ansibase_ansible, auto, yaml, ini
```

**Configuration de `ansibase.yml`** :

```yaml
plugin: ansibase_ansible

host: localhost
port: 5432
database: ansible_inventory
user: ansible
password: "mot_de_passe"

encryption_key: "cle_de_chiffrement"
```

> Le fichier doit se terminer par `ansibase.yml` ou `ansibase.yaml` pour etre reconnu par le plugin.

**Utilisation :**

```bash
# Verifier que le plugin est reconnu
ansible-inventory -i ansibase.yml --list

# Afficher l'arborescence de l'inventaire
ansible-inventory -i ansibase.yml --graph

# Ping de tous les hotes
ansible all -i ansibase.yml -m ping

# Lancer un playbook
ansible-playbook -i ansibase.yml deploy.yml
```

Exemple d'arborescence et de ping via le plugin :

![Utilisation du plugin ansibase : arborescence et ping](docs/ansibase_using.png)

### Mode script (`ansibase-inventory`)

Le script d'inventaire est installe en tant que commande via le package `ansibase`. Il utilise un fichier de configuration INI (`ansibase.ini`).

```bash
cp example.ansibase.ini ansibase.ini
# Editer ansibase.ini avec les parametres de connexion
```

**Utilisation :**

```bash
# Lister l'inventaire complet
ansibase-inventory --list

# Afficher le JSON de maniere lisible
ansibase-inventory --list --pretty

# Variables d'un hote specifique
ansibase-inventory --host mon-serveur

# Fichier de configuration personnalise
ansibase-inventory --list --config /chemin/vers/custom.ini

# Utiliser avec Ansible
ansible all -i <(ansibase-inventory --list) -m ping
ansible-playbook -i <(ansibase-inventory --list) site.yml
```

## Base de donnees

Les migrations Alembic creent automatiquement le schema avec les donnees par defaut : groupes `all` et `ungrouped`, variables Ansible builtin (`ansible_host`, `ansible_port`, `ansible_user`, `ansible_password`, `ansible_become_password`).

Vue des hotes avec psql :

![Hotes dans la base de donnees PostgreSQL](docs/hosts_bd.png)

Exemples d'insertion de donnees via `psql` :

```sql
-- Creer un groupe
INSERT INTO ansibase_groups (name, description, parent_id)
VALUES ('webservers', 'Serveurs web', (SELECT id FROM ansibase_groups WHERE name = 'all'));

-- Creer un hote
INSERT INTO ansibase_hosts (name, description)
VALUES ('web01.example.com', 'Serveur web principal');

-- Associer l'hote au groupe
INSERT INTO ansibase_host_groups (host_id, group_id)
VALUES (
    (SELECT id FROM ansibase_hosts WHERE name = 'web01.example.com'),
    (SELECT id FROM ansibase_groups WHERE name = 'webservers')
);

-- Definir une variable non sensible pour l'hote
INSERT INTO ansibase_host_variables (host_id, var_id, var_value)
VALUES (
    (SELECT id FROM ansibase_hosts WHERE name = 'web01.example.com'),
    (SELECT id FROM ansibase_variables WHERE var_key = 'ansible_host'),
    '192.168.1.10'
);

-- Definir une variable sensible chiffree pour l'hote
INSERT INTO ansibase_host_variables (host_id, var_id, var_value_encrypted)
VALUES (
    (SELECT id FROM ansibase_hosts WHERE name = 'web01.example.com'),
    (SELECT id FROM ansibase_variables WHERE var_key = 'ansible_password'),
    pgp_sym_encrypt('mot_de_passe_ssh', 'cle_de_chiffrement')
);

-- Consulter le catalogue des variables avec leurs alias
SELECT * FROM ansibase_v_variables_catalog;
```

## Licence

Ce projet est distribue sous licence [GPL-3.0](LICENSE).
