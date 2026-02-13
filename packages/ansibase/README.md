# Ansibase

Inventaire Ansible dynamique avec PostgreSQL. Fournit un constructeur d'inventaire, le chiffrement des variables sensibles via pgcrypto, et une CLI de gestion des hotes, groupes et variables.

## Installation

```bash
# -- Core uniquement
pip install ansibase

# -- Avec le plugin et script Ansible
pip install ansibase[ansible]
```

En utilisant le code source :

```bash
# -- Core uniquement
pip install -e packages/ansibase

# -- Avec le plugin et script Ansible
pip install -e "packages/ansibase[ansible]"
```

## Utilisation

### En tant que bibliotheque Python

```python
from ansibase import Database, DatabaseConfig, PgCrypto, InventoryBuilder

config = DatabaseConfig(host="localhost", port=5432, database="ansibase", user="ansibase", password="ansibase")
db = Database(config)
crypto = PgCrypto("ma_cle_de_chiffrement")

session = db.get_session()
builder = InventoryBuilder(session, crypto)
inventory = builder.build()
```

### Script de migrations (`ansibase-db`)

```bash
# Appliquer les migrations
ansibase-db upgrade --config ansibase.ini

# Voir les migrations
ansibase-db history --config ansibase.ini
```

### CLI de gestion (`ansibase-manage`)

Gestion des hotes, groupes et variables directement depuis le terminal.

```bash
ansibase-manage --help
ansibase-manage -c ansibase.ini host list
ansibase-manage --json group list --tree
```

#### Hotes (`host`)

| Commande                           | Description                                                                         |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| `host list`                        | Lister les hotes (`--active/--inactive`, `--group`, `--search`)                     |
| `host show <ref>`                  | Details d'un hote (info, groupes, variables). `--reveal` pour les valeurs sensibles |
| `host create <name>`               | Creer un hote (`--description`, `--inactive`)                                       |
| `host update <ref>`                | Modifier un hote (`--name`, `--description`, `--active/--inactive`)                 |
| `host delete <ref>`                | Supprimer un hote (`--yes` pour confirmer)                                          |
| `host add-group <ref> <group>`     | Ajouter un hote a un groupe                                                         |
| `host remove-group <ref> <group>`  | Retirer un hote d'un groupe                                                         |
| `host set-var <ref> <key> <value>` | Assigner une variable a un hote (upsert)                                            |
| `host unset-var <ref> <key>`       | Retirer une variable d'un hote                                                      |
| `host import <fichier.yml>`        | Importer des hotes et variables depuis un fichier YAML                              |

#### Groupes (`group`)

| Commande                            | Description                                                       |
| ----------------------------------- | ----------------------------------------------------------------- |
| `group list`                        | Lister les groupes (`--tree` pour l'arborescence)                 |
| `group show <ref>`                  | Details d'un groupe. `--inherited` pour les variables heritees    |
| `group create <name>`               | Creer un groupe (`--description`, `--parent`)                     |
| `group update <ref>`                | Modifier un groupe (`--name`, `--description`, `--parent`)        |
| `group delete <ref>`                | Supprimer un groupe (`--yes`). `all` et `ungrouped` sont proteges |
| `group set-var <ref> <key> <value>` | Assigner une variable a un groupe (upsert)                        |
| `group unset-var <ref> <key>`       | Retirer une variable d'un groupe                                  |
| `group import <fichier.yml>`        | Importer des groupes au format inventaire Ansible                 |

#### Variables (`var`)

| Commande               | Description                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------- |
| `var list`             | Lister le catalogue (`--sensitive`, `--builtin`, `--type`)                            |
| `var create <var_key>` | Creer une variable (`--description`, `--sensitive`, `--type`, `--default`, `--regex`) |
| `var update <ref>`     | Modifier les metadonnees d'une variable                                               |
| `var delete <ref>`     | Supprimer une variable (`--force` pour les builtins)                                  |

> `<ref>` accepte un ID numerique ou un nom (hostname, group name, var_key).

#### Import YAML

**Import d'hotes** — format plat (un hote, `--name` optionnel) ou multi-hotes :

```yaml
# Format plat (web01.yml) — hostname deduit du nom de fichier
ansible_host: 192.168.1.10
ansible_user: deploy

# Format multi-hotes (hosts.yml)
web01.example.com:
  ansible_host: 192.168.1.10
web02.example.com:
  ansible_host: 192.168.1.11
```

```bash
ansibase-manage host import web01.yml
ansibase-manage host import hosts.yml --dry-run
```

**Import de groupes** — format inventaire Ansible avec `hosts`, `vars` et `children` :

```yaml
webservers:
  hosts:
    web01.example.com:
      ansible_host: 192.168.1.10
  vars:
    http_port: 80
  children:
    frontend:
      hosts:
        web01.example.com:
```

```bash
ansibase-manage group import inventory.yml
```

### Script d'inventaire dynamique (`ansibase-inventory`)

```bash
# Lister l'inventaire complet
ansibase-inventory --list --config ansibase.ini

# Variables d'un hote
ansibase-inventory --host monserveur --config ansibase.ini
```

### Plugin Ansible (`ansibase_ansible`)

Ajouter dans `ansible.cfg` :

```ini
[defaults]
inventory_plugins = ./inventory_plugins

[inventory]
enable_plugins = ansibase_ansible, auto
```

Creer le lien symbolique du plugin dans votre repertoire des plugins :

```bash
ln -s $(python -c "from pathlib import Path; import ansibase.ansible; print(Path(ansibase.ansible.__file__).parent)")/ansibase_ansible.py inventory_plugins/ansibase_ansible.py
```

Puis utiliser avec un fichier `ansibase.yml` :

```yaml
plugin: ansibase_ansible
host: localhost
port: 5432
database: ansibase
user: ansibase
password: "mon_mot_de_passe"
encryption_key: "ma_cle"
```
