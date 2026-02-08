"""
Tests CRUD utilisateurs et API Keys
"""


# ── Créer un utilisateur


def test_creer_utilisateur(client, auth_headers):
    """Superuser cree un utilisateur → 201, retourne LoginResponse avec cle API par defaut"""
    resp = client.post(
        "/api/v1/users",
        json={"username": "newuser", "password": "secret123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()

    # la reponse est un LoginResponse (user + cle API par defaut)
    assert data["user"]["username"] == "newuser"
    assert data["user"]["is_superuser"] is False
    assert data["user"]["is_active"] is True
    assert "api_key" in data
    assert len(data["api_key"]) > 20
    assert data["key_prefix"] == data["api_key"][:12]


def test_creer_utilisateur_sans_superuser(client, regular_auth_headers):
    """Non-superuser ne peut pas creer → 403"""
    resp = client.post(
        "/api/v1/users",
        json={"username": "another", "password": "secret"},
        headers=regular_auth_headers,
    )
    assert resp.status_code == 403


def test_creer_utilisateur_duplique(client, auth_headers):
    """Username duplique → 409"""
    client.post(
        "/api/v1/users",
        json={"username": "dupuser", "password": "pass1"},
        headers=auth_headers,
    )
    resp = client.post(
        "/api/v1/users",
        json={"username": "dupuser", "password": "pass2"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


# ── Lister les utilisateurs


def test_lister_utilisateurs(client, auth_headers):
    """Liste paginee des utilisateurs"""
    resp = client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1


# ── Voir un utilisateur


def test_voir_utilisateur_par_username(client, auth_headers):
    """Voir un utilisateur par username"""
    resp = client.get("/api/v1/users/admin", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_voir_utilisateur_par_id(client, auth_headers):
    """Voir un utilisateur par ID"""
    resp = client.get("/api/v1/users/1", headers=auth_headers)
    assert resp.status_code == 200


def test_voir_utilisateur_inexistant(client, auth_headers):
    """Utilisateur introuvable → 404"""
    resp = client.get("/api/v1/users/inconnu", headers=auth_headers)
    assert resp.status_code == 404


# ── Modifier un utilisateur


def test_modifier_utilisateur(client, auth_headers):
    """Modifier un utilisateur"""
    # on cree d'abord
    client.post(
        "/api/v1/users",
        json={"username": "modifiable", "password": "old"},
        headers=auth_headers,
    )
    resp = client.put(
        "/api/v1/users/modifiable",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# ── Supprimer un utilisateur


def test_supprimer_utilisateur(client, auth_headers):
    """Supprimer un utilisateur → 204"""
    client.post(
        "/api/v1/users",
        json={"username": "todelete", "password": "pass"},
        headers=auth_headers,
    )
    resp = client.delete("/api/v1/users/todelete", headers=auth_headers)
    assert resp.status_code == 204

    # on verifie qu'il n'existe plus
    resp = client.get("/api/v1/users/todelete", headers=auth_headers)
    assert resp.status_code == 404


# ── Générer une API Key


def test_generer_api_key(client, auth_headers):
    """Generer une API Key → 201, retourne ApiKeyResponse avec key_value"""
    resp = client.post(
        "/api/v1/users/admin/api-keys",
        json={"name": "ma-cle-test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()

    # la reponse contient la cle en clair dans key_value
    assert "key_value" in data
    assert len(data["key_value"]) > 20
    assert data["name"] == "ma-cle-test"
    assert data["is_active"] is True
    assert data["expires_at"] is None


def test_generer_api_key_sans_expiration(client, auth_headers):
    """API Key sans expiration (expires_at=null)"""
    resp = client.post(
        "/api/v1/users/admin/api-keys",
        json={"name": "permanent-key"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is None


# ── Lister ses API Keys


def test_lister_api_keys(client, auth_headers):
    """Lister les API keys — la cle en clair n'est pas dechiffree"""
    # on cree une cle
    client.post(
        "/api/v1/users/admin/api-keys",
        json={"name": "list-test-key"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/users/admin/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert isinstance(keys, list)
    assert len(keys) >= 1

    # la valeur de la cle n'est pas dechiffree dans le listing
    for key in keys:
        assert key["key_value"] == "**************"
        assert "key_prefix" in key


# ── Révoquer une API Key


def test_revoquer_api_key(client, auth_headers):
    """Revoquer une API key → 204"""
    # on cree une cle
    create_resp = client.post(
        "/api/v1/users/admin/api-keys",
        json={"name": "revoke-me"},
        headers=auth_headers,
    )
    key_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/users/admin/api-keys/{key_id}", headers=auth_headers)
    assert resp.status_code == 204
