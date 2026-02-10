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
ansibase-db --config ansibase.ini upgrade 

# Voir les migrations
ansibase-inventory --host monserveur --config ansibase.ini
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
inventory_plugins = <chemin_vers_site-packages>/ansibase/ansible

[inventory]
enable_plugins = ansibase-ansible, auto
```

`<chemin_vers_site-packages>` peut etre obtenu en utilisant la commande

```bash
python -c "from pathlib import Path; import ansibase.ansible; print(Path(ansibase.ansible.__file__).parent.parent.parent)"
```

Puis utiliser avec un fichier `ansibase.yml` :

```yaml
plugin: ansibase-ansible
host: localhost
port: 5432
database: ansibase
user: ansibase
password: "mon_mot_de_passe"
encryption_key: "ma_cle"
```
