"""
Tests export inventaire Ansible
"""


def _setup_inventory_data(client, auth_headers):
    """Cree des donnees de test pour l'inventaire"""
    # hote
    client.post("/api/v1/hosts", json={"name": "inv-web01"}, headers=auth_headers)
    # groupe
    client.post(
        "/api/v1/groups",
        json={"name": "inv-webservers", "parent": "all"},
        headers=auth_headers,
    )
    # assigner l'hote au groupe
    client.post(
        "/api/v1/hosts/inv-web01/groups",
        json={"group": "inv-webservers"},
        headers=auth_headers,
    )
    # assigner des variables a l'hote
    client.post(
        "/api/v1/hosts/inv-web01/variables",
        json={"variable": "ansible_host", "value": "192.168.1.10"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/hosts/inv-web01/variables",
        json={"variable": "ansible_user", "value": "deploy"},
        headers=auth_headers,
    )


# ── Export inventaire complet


def test_export_inventaire_complet(client, auth_headers):
    """Export JSON Ansible standard"""
    _setup_inventory_data(client, auth_headers)

    resp = client.get("/api/v1/inventory", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    # structure Ansible standard
    assert "_meta" in data
    assert "hostvars" in data["_meta"]

    # on verifie que l'hote est dans les hostvars
    assert "inv-web01" in data["_meta"]["hostvars"]
    hostvars = data["_meta"]["hostvars"]["inv-web01"]
    assert hostvars["ansible_host"] == "192.168.1.10"
    assert hostvars["ansible_user"] == "deploy"


# ── Variables d'un hôte


def test_export_host_vars(client, auth_headers):
    """Variables d'un hôte spécifique"""
    _setup_inventory_data(client, auth_headers)

    resp = client.get("/api/v1/inventory/hosts/inv-web01", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ansible_host"] == "192.168.1.10"


def test_export_host_vars_inexistant(client, auth_headers):
    """Hôte inexistant → 404"""
    resp = client.get("/api/v1/inventory/hosts/ghost_host", headers=auth_headers)
    assert resp.status_code == 404


# ── Graphe des groupes


def test_inventory_graph(client, auth_headers):
    """Arborescence des groupes"""
    resp = client.get("/api/v1/inventory/graph", headers=auth_headers)
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) >= 1
    assert tree[0]["name"] == "all"
