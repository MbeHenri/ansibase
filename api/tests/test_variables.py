"""
Tests CRUD Variables et Alias
"""

import pytest


# ── Créer une variable


def test_creer_variable(client, auth_headers):
    """Créer une variable simple → 201"""
    resp = client.post(
        "/api/v1/variables",
        json={
            "var_key": "site_domain",
            "description": "Domaine du site",
            "var_type": "string",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["var_key"] == "site_domain"
    assert data["is_sensitive"] is False
    assert data["is_ansible_builtin"] is False


def test_creer_variable_sensible(client, auth_headers):
    """Créer une variable sensible → 201"""
    resp = client.post(
        "/api/v1/variables",
        json={"var_key": "db_password", "is_sensitive": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["is_sensitive"] is True


def test_creer_variable_dupliquee(client, auth_headers):
    """var_key dupliqué → 409"""
    client.post(
        "/api/v1/variables",
        json={"var_key": "dup_var"},
        headers=auth_headers,
    )
    resp = client.post(
        "/api/v1/variables",
        json={"var_key": "dup_var"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


# ── Lister les variables


def test_lister_variables(client, auth_headers):
    """Liste paginée du catalogue"""
    resp = client.get("/api/v1/variables", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 5  # au moins les 5 builtins


def test_lister_variables_filtre_sensitive(client, auth_headers):
    """Filtre is_sensitive=true"""
    resp = client.get("/api/v1/variables?is_sensitive=true", headers=auth_headers)
    assert resp.status_code == 200
    for v in resp.json()["items"]:
        assert v["is_sensitive"] is True


def test_lister_variables_filtre_builtin(client, auth_headers):
    """Filtre is_ansible_builtin=true"""
    resp = client.get("/api/v1/variables?is_ansible_builtin=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for v in data["items"]:
        assert v["is_ansible_builtin"] is True


# ── Voir une variable


def test_voir_variable_par_nom(client, auth_headers):
    """Voir par var_key"""
    resp = client.get("/api/v1/variables/ansible_host", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["var_key"] == "ansible_host"


def test_voir_variable_par_id(client, auth_headers):
    """Voir par ID"""
    # on recupere l'id d'abord
    list_resp = client.get(
        "/api/v1/variables?is_ansible_builtin=true", headers=auth_headers
    )
    var_id = list_resp.json()["items"][0]["id"]
    resp = client.get(f"/api/v1/variables/{var_id}", headers=auth_headers)
    assert resp.status_code == 200


def test_voir_variable_inexistante(client, auth_headers):
    """Variable introuvable → 404"""
    resp = client.get("/api/v1/variables/inexistante", headers=auth_headers)
    assert resp.status_code == 404


# ── Modifier une variable


def test_modifier_variable(client, auth_headers):
    """Modifier la description"""
    client.post(
        "/api/v1/variables",
        json={"var_key": "modif_var"},
        headers=auth_headers,
    )
    resp = client.put(
        "/api/v1/variables/modif_var",
        json={"description": "Nouvelle description"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Nouvelle description"


def test_modifier_is_sensitive_avec_valeurs_existantes(client, auth_headers, db):
    """Interdire le changement de is_sensitive si des valeurs existent"""
    from app.models import HostVariable, Variable, Host

    # on cree une variable et un hote
    client.post(
        "/api/v1/variables",
        json={"var_key": "test_sens_change", "is_sensitive": False},
        headers=auth_headers,
    )
    var = db.execute(
        __import__("sqlalchemy")
        .select(Variable)
        .where(Variable.var_key == "test_sens_change")
    ).scalar_one()

    # on cree un hote et on affecte la variable
    host = Host(name="test-host-sens")
    db.add(host)
    db.flush()
    hv = HostVariable(host_id=host.id, var_id=var.id, var_value="some_value")
    db.add(hv)
    db.flush()

    resp = client.put(
        "/api/v1/variables/test_sens_change",
        json={"is_sensitive": True},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ── Supprimer une variable


def test_supprimer_variable_custom(client, auth_headers):
    """Supprimer une variable custom → 204"""
    client.post(
        "/api/v1/variables",
        json={"var_key": "to_delete"},
        headers=auth_headers,
    )
    resp = client.delete("/api/v1/variables/to_delete", headers=auth_headers)
    assert resp.status_code == 204


def test_supprimer_builtin_sans_force(client, auth_headers):
    """Supprimer un builtin sans force → 403"""
    resp = client.delete("/api/v1/variables/ansible_host", headers=auth_headers)
    assert resp.status_code == 403


def test_supprimer_builtin_avec_force(client, auth_headers):
    """Supprimer un builtin avec force=true → 204"""
    resp = client.delete(
        "/api/v1/variables/ansible_become_password?force=true", headers=auth_headers
    )
    assert resp.status_code == 204


# ── Créer un alias


def test_creer_alias(client, auth_headers):
    """Créer un alias entre deux variables → 201"""
    # on cree la variable source
    client.post(
        "/api/v1/variables",
        json={"var_key": "site_host"},
        headers=auth_headers,
    )
    resp = client.post(
        "/api/v1/variables/ansible_host/aliases",
        json={"source_variable": "site_host"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["alias_var_key"] == "ansible_host"
    assert data["source_var_key"] == "site_host"


def test_creer_alias_self_referencing(client, auth_headers):
    """Alias auto-référençant → 400"""
    resp = client.post(
        "/api/v1/variables/ansible_user/aliases",
        json={"source_variable": "ansible_user"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ── Lister les alias


def test_lister_alias(client, auth_headers):
    """Lister les alias d'une variable"""
    # on cree les donnees
    client.post(
        "/api/v1/variables", json={"var_key": "my_source"}, headers=auth_headers
    )
    client.post("/api/v1/variables", json={"var_key": "my_alias"}, headers=auth_headers)
    client.post(
        "/api/v1/variables/my_alias/aliases",
        json={"source_variable": "my_source"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/variables/my_alias/aliases", headers=auth_headers)
    assert resp.status_code == 200
    aliases = resp.json()
    assert len(aliases) >= 1


# ── Supprimer un alias


def test_supprimer_alias(client, auth_headers):
    """Supprimer un alias → 204"""
    client.post("/api/v1/variables", json={"var_key": "src_del"}, headers=auth_headers)
    client.post(
        "/api/v1/variables", json={"var_key": "alias_del"}, headers=auth_headers
    )
    create_resp = client.post(
        "/api/v1/variables/alias_del/aliases",
        json={"source_variable": "src_del"},
        headers=auth_headers,
    )
    alias_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/variable-aliases/{alias_id}", headers=auth_headers)
    assert resp.status_code == 204
