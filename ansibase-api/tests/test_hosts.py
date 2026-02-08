"""
Tests CRUD Hôtes
"""


# ── Créer un hôte


def test_creer_hote(client, auth_headers):
    """Créer un hôte → 201"""
    resp = client.post(
        "/api/v1/hosts",
        json={"name": "web01", "description": "Serveur web 1"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "web01"
    assert resp.json()["is_active"] is True


def test_creer_hote_duplique(client, auth_headers):
    """Nom dupliqué → 409"""
    client.post("/api/v1/hosts", json={"name": "dup_host"}, headers=auth_headers)
    resp = client.post("/api/v1/hosts", json={"name": "dup_host"}, headers=auth_headers)
    assert resp.status_code == 409


# ── Lister les hôtes


def test_lister_hotes(client, auth_headers):
    """Liste paginée"""
    client.post("/api/v1/hosts", json={"name": "list_h1"}, headers=auth_headers)
    resp = client.get("/api/v1/hosts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_lister_hotes_filtre_active(client, auth_headers):
    """Filtre is_active"""
    client.post(
        "/api/v1/hosts",
        json={"name": "inactive_h", "is_active": False},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/hosts?is_active=false", headers=auth_headers)
    assert resp.status_code == 200
    for h in resp.json()["items"]:
        assert h["is_active"] is False


def test_lister_hotes_filtre_groupe(client, auth_headers):
    """Filtre par groupe"""
    client.post("/api/v1/hosts", json={"name": "grp_h1"}, headers=auth_headers)
    client.post("/api/v1/groups", json={"name": "filter_grp", "parent": "all"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/grp_h1/groups",
        json={"group": "filter_grp"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/hosts?group=filter_grp", headers=auth_headers)
    assert resp.status_code == 200
    names = [h["name"] for h in resp.json()["items"]]
    assert "grp_h1" in names


# ── Voir un hôte


def test_voir_hote_par_nom(client, auth_headers):
    """Voir un hôte par nom"""
    client.post("/api/v1/hosts", json={"name": "see_host"}, headers=auth_headers)
    resp = client.get("/api/v1/hosts/see_host", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "see_host"


def test_voir_hote_par_id(client, auth_headers):
    """Voir un hôte par ID"""
    create = client.post("/api/v1/hosts", json={"name": "see_id_h"}, headers=auth_headers)
    hid = create.json()["id"]
    resp = client.get(f"/api/v1/hosts/{hid}", headers=auth_headers)
    assert resp.status_code == 200


# ── Modifier un hôte


def test_modifier_hote(client, auth_headers):
    """Modifier un hôte → 200"""
    client.post("/api/v1/hosts", json={"name": "mod_host"}, headers=auth_headers)
    resp = client.put(
        "/api/v1/hosts/mod_host",
        json={"description": "Updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"


# ── Supprimer un hôte


def test_supprimer_hote(client, auth_headers):
    """Supprimer un hôte → 204"""
    client.post("/api/v1/hosts", json={"name": "del_host"}, headers=auth_headers)
    resp = client.delete("/api/v1/hosts/del_host", headers=auth_headers)
    assert resp.status_code == 204

    # on verifie qu'il n'existe plus
    resp = client.get("/api/v1/hosts/del_host", headers=auth_headers)
    assert resp.status_code == 404


# ── Groupes d'un hôte


def test_ajouter_hote_a_groupe(client, auth_headers):
    """Ajouter à un groupe par nom → 201"""
    client.post("/api/v1/hosts", json={"name": "grp_add_h"}, headers=auth_headers)
    client.post("/api/v1/groups", json={"name": "webservers", "parent": "all"}, headers=auth_headers)
    resp = client.post(
        "/api/v1/hosts/grp_add_h/groups",
        json={"group": "webservers"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_ajouter_hote_meme_groupe(client, auth_headers):
    """Ajouter au même groupe → 409"""
    client.post("/api/v1/hosts", json={"name": "dup_grp_h"}, headers=auth_headers)
    client.post("/api/v1/groups", json={"name": "dup_test_grp", "parent": "all"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/dup_grp_h/groups",
        json={"group": "dup_test_grp"},
        headers=auth_headers,
    )
    resp = client.post(
        "/api/v1/hosts/dup_grp_h/groups",
        json={"group": "dup_test_grp"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_retirer_hote_groupe(client, auth_headers):
    """Retirer d'un groupe → 204"""
    client.post("/api/v1/hosts", json={"name": "rm_grp_h"}, headers=auth_headers)
    client.post("/api/v1/groups", json={"name": "rm_test_grp", "parent": "all"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/rm_grp_h/groups",
        json={"group": "rm_test_grp"},
        headers=auth_headers,
    )
    resp = client.delete("/api/v1/hosts/rm_grp_h/groups/rm_test_grp", headers=auth_headers)
    assert resp.status_code == 204


# ── Lister les groupes d'un hôte


def test_lister_groupes_hote(client, auth_headers):
    """Lister les groupes d'un hôte"""
    client.post("/api/v1/hosts", json={"name": "list_grp_h"}, headers=auth_headers)
    client.post("/api/v1/groups", json={"name": "list_test_grp", "parent": "all"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/list_grp_h/groups",
        json={"group": "list_test_grp"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/hosts/list_grp_h/groups", headers=auth_headers)
    assert resp.status_code == 200
    assert "list_test_grp" in resp.json()


# ── Variables d'un hôte


def test_affecter_variable_hote(client, auth_headers):
    """Affecter ansible_host par nom → 201"""
    client.post("/api/v1/hosts", json={"name": "var_host"}, headers=auth_headers)
    resp = client.post(
        "/api/v1/hosts/var_host/variables",
        json={"variable": "ansible_host", "value": "10.0.0.1"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["var_key"] == "ansible_host"
    assert resp.json()["value"] == "10.0.0.1"


def test_affecter_variable_sensible(client, auth_headers):
    """Variable sensible → valeur masquée dans la réponse"""
    client.post("/api/v1/hosts", json={"name": "sens_host"}, headers=auth_headers)
    resp = client.post(
        "/api/v1/hosts/sens_host/variables",
        json={"variable": "ansible_password", "value": "secret123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["value"] == "****"
    assert resp.json()["is_sensitive"] is True


def test_lister_variables_hote_masquees(client, auth_headers):
    """Variables sensibles masquées par défaut"""
    client.post("/api/v1/hosts", json={"name": "mask_host"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/mask_host/variables",
        json={"variable": "ansible_password", "value": "secret"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/hosts/mask_host/variables", headers=auth_headers)
    assert resp.status_code == 200
    for v in resp.json():
        if v["is_sensitive"]:
            assert v["value"] == "****"


def test_lister_variables_hote_reveal(client, auth_headers):
    """Variables sensibles déchiffrées avec reveal=true"""
    client.post("/api/v1/hosts", json={"name": "reveal_host"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/reveal_host/variables",
        json={"variable": "ansible_password", "value": "revealed_secret"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/hosts/reveal_host/variables?reveal=true", headers=auth_headers)
    assert resp.status_code == 200
    pw = next(v for v in resp.json() if v["var_key"] == "ansible_password")
    assert pw["value"] == "revealed_secret"


def test_modifier_variable_hote(client, auth_headers):
    """Modifier une valeur → 200"""
    client.post("/api/v1/hosts", json={"name": "upd_var_h"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/upd_var_h/variables",
        json={"variable": "ansible_host", "value": "10.0.0.1"},
        headers=auth_headers,
    )
    resp = client.put(
        "/api/v1/hosts/upd_var_h/variables/ansible_host",
        json={"variable": "ansible_host", "value": "10.0.0.2"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "10.0.0.2"


def test_retirer_variable_hote(client, auth_headers):
    """Retirer une variable → 204"""
    client.post("/api/v1/hosts", json={"name": "rm_var_h"}, headers=auth_headers)
    client.post(
        "/api/v1/hosts/rm_var_h/variables",
        json={"variable": "ansible_host", "value": "10.0.0.1"},
        headers=auth_headers,
    )
    resp = client.delete("/api/v1/hosts/rm_var_h/variables/ansible_host", headers=auth_headers)
    assert resp.status_code == 204
