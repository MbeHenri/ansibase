# Ansibase

Inventaire Ansible dynamique avec PostgreSQL.

## Installation

```bash
# -- Core uniquement
pip install ansibase

# -- Avec le plugin et script Ansible
pip install ansibase[ansible]
```

En utilisant le code source

```bash
# -- Core uniquement
pip install -e packages/ansibase

# -- Avec le plugin et script Ansible
pip install -e "packages/ansibase[ansible]"
```

## Utilisation

### En tant que bibliothèque Python

```python
from ansibase import Database, DatabaseConfig, PgCrypto, InventoryBuilder

config = DatabaseConfig(host="localhost", port=5432, database="ansibase", user="ansibase", password="ansibase")
db = Database(config)
crypto = PgCrypto("ma_cle_de_chiffrement")

session = db.get_session()
builder = InventoryBuilder(session, crypto)
inventory = builder.build()
```

### Script pour gerer la base de donnees

```bash
# Appliquer les migrations
ansibase-db upgrade --config ansibase.ini 

# Voir les migrations
ansibase-db history --config ansibase.ini
```

### Script d'inventaire dynamique

```bash
# Lister l'inventaire complet
ansibase-inventory --list --config ansibase.ini

# Variables d'un hôte
ansibase-inventory --host monserveur --config ansibase.ini
```

### Plugin Ansible

Ajouter dans `ansible.cfg` :

```ini
[defaults]
# ton repertoire des inventaires
inventory_plugins = ./inventory_plugins

[inventory]
enable_plugins = ansibase_ansible, auto
```

cree le lien symbolique du plugin dans votre repertoire des plugins

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
