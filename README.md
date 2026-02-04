# ansibase

Base de donnees pour Ansible pour gerer son inventaire ( plugin + base de donnees + interfaces accessibles a tous)

## Structure

```txt
.
├── ansibase                       # package gerant la base de donnees d'ansibase
│   ├── builder.py                   # + module pour construire l'inventaire
│   ├── crypto.py                    # + module pour chiffrer des donnees
│   ├── database.py                  # + module de connexion a la base de donnees
│   ├── graph.py                     # + module des graphes de groupes
│   ├── models                       # + module des modeles des groups, des hotes et des variables
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── group.py
│   │   ├── host.py
│   │   └── variable.py
│   └── schemas                    # + repertoires des schemas de BD
│       ├── init.sql                 # - script sql pour initier ansibase
│       └── roolback.init.sql        # - script sql pour le supprimer
├── ansibase_plugin.py             # plugin d'inventaire pour ansile
├── example.inventory.ansibase.yml # configuration d'exemple du plugin
├── inventory.ansibase.py          # script d'inventaire pour ansible
├── example.ansibase.ini           # configuration d'exemple du script
└── requirements.txt
```

Les fichiers de configurations `example.inventory.ansibase.yml` et `example.ansibase.ini` doivent etre renonne respectivement par `inventory.ansibase.yml` et `ansibase.ini` pour etre detecte automatiquement.
