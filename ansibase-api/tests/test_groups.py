"""
Tests CRUD Groupes
"""


# ── Créer un groupe


def test_creer_groupe(client, auth_headers):
    """Créer un groupe avec parent par nom → 201"""
    resp = client.post(
        "/api/v1/groups",
        json={"name": "webservers", "description": "Serveurs web", "parent": "all"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "webservers"


def test_creer_groupe_duplique(client, auth_headers):
    """Nom dupliqué → 409"""
    client.post("/api/v1/groups", json={"name": "dup_grp"}, headers=auth_headers)
    resp = client.post("/api/v1/groups", json={"name": "dup_grp"}, headers=auth_headers)
    assert resp.status_code == 409


# ── Lister les groupes


def test_lister_groupes(client, auth_headers):
    """Liste paginée (all et ungrouped présents)"""
    resp = client.get("/api/v1/groups", headers=auth_headers)
    assert resp.status_code == 200
    names = [g["name"] for g in resp.json()["items"]]
    assert "all" in names
    assert "ungrouped" in names


def test_lister_groupes_tree(client, auth_headers):
    """Vue arborescente"""
    resp = client.get("/api/v1/groups?tree=true", headers=auth_headers)
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) >= 1
    assert tree[0]["name"] == "all"


# ── Voir un groupe


def test_voir_groupe_par_nom(client, auth_headers):
    """Voir un groupe par nom"""
    resp = client.get("/api/v1/groups/all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "all"
    assert "children" in data
    assert "ungrouped" in data["children"]


# ── Modifier un groupe


def test_modifier_groupe(client, auth_headers):
    """Modifier la description"""
    client.post("/api/v1/groups", json={"name": "modif_grp"}, headers=auth_headers)
    resp = client.put(
        "/api/v1/groups/modif_grp",
        json={"description": "Nouvelle desc"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Nouvelle desc"


def test_renommer_all_interdit(client, auth_headers):
    """Renommer 'all' → 400"""
    resp = client.put(
        "/api/v1/groups/all",
        json={"name": "root"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ── Supprimer un groupe


def test_supprimer_ungrouped_interdit(client, auth_headers):
    """Supprimer 'ungrouped' → 400"""
    resp = client.delete("/api/v1/groups/ungrouped", headers=auth_headers)
    assert resp.status_code == 400


def test_supprimer_groupe_custom(client, auth_headers):
    """Supprimer un groupe custom → 204"""
    client.post("/api/v1/groups", json={"name": "to_del_grp"}, headers=auth_headers)
    resp = client.delete("/api/v1/groups/to_del_grp", headers=auth_headers)
    assert resp.status_code == 204


# ── Lister les hôtes d'un groupe


def test_lister_hotes_groupe(client, auth_headers):
    """Liste vide pour un groupe sans hôtes"""
    resp = client.get("/api/v1/groups/all/hosts", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Variables de groupe


def test_affecter_variable_groupe(client, auth_headers):
    """Affecter une variable à un groupe → 201"""
    client.post("/api/v1/groups", json={"name": "var_grp", "parent": "all"}, headers=auth_headers)
    client.post(
        "/api/v1/variables",
        json={"var_key": "ntp_server", "var_type": "string"},
        headers=auth_headers,
    )
    resp = client.post(
        "/api/v1/groups/var_grp/variables",
        json={"variable": "ntp_server", "value": "ntp.example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["var_key"] == "ntp_server"
    assert resp.json()["value"] == "ntp.example.com"


def test_lister_variables_groupe(client, auth_headers):
    """Lister les variables d'un groupe"""
    client.post("/api/v1/groups", json={"name": "list_var_grp", "parent": "all"}, headers=auth_headers)
    client.post(
        "/api/v1/variables",
        json={"var_key": "env_var"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/groups/list_var_grp/variables",
        json={"variable": "env_var", "value": "production"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/groups/list_var_grp/variables", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_modifier_variable_groupe(client, auth_headers):
    """Modifier la valeur d'une variable de groupe → 200"""
    client.post("/api/v1/groups", json={"name": "upd_var_grp", "parent": "all"}, headers=auth_headers)
    client.post("/api/v1/variables", json={"var_key": "upd_var"}, headers=auth_headers)
    client.post(
        "/api/v1/groups/upd_var_grp/variables",
        json={"variable": "upd_var", "value": "old"},
        headers=auth_headers,
    )
    resp = client.put(
        "/api/v1/groups/upd_var_grp/variables/upd_var",
        json={"variable": "upd_var", "value": "new"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "new"


def test_retirer_variable_groupe(client, auth_headers):
    """Retirer une variable d'un groupe → 204"""
    client.post("/api/v1/groups", json={"name": "rm_var_grp", "parent": "all"}, headers=auth_headers)
    client.post("/api/v1/variables", json={"var_key": "rm_var"}, headers=auth_headers)
    client.post(
        "/api/v1/groups/rm_var_grp/variables",
        json={"variable": "rm_var", "value": "val"},
        headers=auth_headers,
    )
    resp = client.delete("/api/v1/groups/rm_var_grp/variables/rm_var", headers=auth_headers)
    assert resp.status_code == 204


# ── Variables requises


def test_ajouter_variable_requise(client, auth_headers):
    """Ajouter une variable requise → 201"""
    client.post("/api/v1/groups", json={"name": "req_grp", "parent": "all"}, headers=auth_headers)
    client.post("/api/v1/variables", json={"var_key": "req_var"}, headers=auth_headers)
    resp = client.post(
        "/api/v1/groups/req_grp/required-variables",
        json={"variable": "req_var", "is_required": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["is_required"] is True


def test_lister_variables_requises(client, auth_headers):
    """Lister les variables requises du groupe 'all'"""
    resp = client.get("/api/v1/groups/all/required-variables", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 5  # les builtins


def test_retirer_variable_requise(client, auth_headers):
    """Retirer une variable requise → 204"""
    client.post("/api/v1/groups", json={"name": "rm_req_grp", "parent": "all"}, headers=auth_headers)
    client.post("/api/v1/variables", json={"var_key": "rm_req_var"}, headers=auth_headers)
    client.post(
        "/api/v1/groups/rm_req_grp/required-variables",
        json={"variable": "rm_req_var", "is_required": True},
        headers=auth_headers,
    )
    resp = client.delete(
        "/api/v1/groups/rm_req_grp/required-variables/rm_req_var", headers=auth_headers
    )
    assert resp.status_code == 204
