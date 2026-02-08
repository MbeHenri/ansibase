"""
Tests d'authentification : login + API Key
"""


# ── Login


def test_login_ok(client, admin_user):
    """Login avec identifiants valides → 200, retourne LoginResponse avec cle API par defaut"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # la reponse contient le user et la cle API par defaut dechiffree
    assert data["user"]["username"] == "admin"
    assert "api_key" in data
    assert len(data["api_key"]) > 20
    assert data["key_prefix"] == data["api_key"][:12]


def test_login_mauvais_password(client, admin_user):
    """Login avec mauvais mot de passe → 401"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_utilisateur_inexistant(client):
    """Login avec username inexistant → 401"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "nope"},
    )
    assert resp.status_code == 401


def test_login_puis_utiliser_cle(client, admin_user):
    """La cle obtenue via login permet d'acceder aux endpoints proteges"""
    # on se connecte pour recuperer la cle API par defaut
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    api_key = resp.json()["api_key"]

    # on utilise la cle pour acceder a un endpoint protege
    resp2 = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp2.status_code == 200


# ── API Key


def test_request_sans_header(client):
    """Requete sans header Authorization → 403"""
    resp = client.get("/api/v1/users")
    assert resp.status_code == 403


def test_request_avec_cle_invalide(client):
    """Requete avec cle invalide → 401"""
    resp = client.get(
        "/api/v1/users", headers={"Authorization": "Bearer cle_bidon_invalide"}
    )
    assert resp.status_code == 401


def test_request_avec_cle_valide(client, auth_headers):
    """Requete avec cle valide → 200"""
    resp = client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200


def test_non_superuser_acces_restreint(client, regular_auth_headers):
    """Non-superuser ne peut pas lister les utilisateurs → 403"""
    resp = client.get("/api/v1/users", headers=regular_auth_headers)
    assert resp.status_code == 403
