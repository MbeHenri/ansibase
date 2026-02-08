"""
Tests Audit Logs
"""


# ── Logs d'audit


def test_audit_logs_apres_actions(client, auth_headers):
    """Les actions CRUD generent des logs d'audit"""
    # on effectue quelques actions
    client.post("/api/v1/hosts", json={"name": "audit-host"}, headers=auth_headers)
    client.post("/api/v1/variables", json={"var_key": "audit_var"}, headers=auth_headers)

    # on consulte les logs
    resp = client.get("/api/v1/audit-logs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2

    actions = [log["action"] for log in data["items"]]
    assert "CREATE" in actions


def test_audit_filtre_action(client, auth_headers):
    """Filtrer par action"""
    client.post("/api/v1/hosts", json={"name": "audit-filter-h"}, headers=auth_headers)

    resp = client.get("/api/v1/audit-logs?action=CREATE", headers=auth_headers)
    assert resp.status_code == 200
    for log in resp.json()["items"]:
        assert log["action"] == "CREATE"


def test_audit_filtre_resource_type(client, auth_headers):
    """Filtrer par resource_type"""
    client.post("/api/v1/hosts", json={"name": "audit-rt-h"}, headers=auth_headers)

    resp = client.get("/api/v1/audit-logs?resource_type=host", headers=auth_headers)
    assert resp.status_code == 200
    for log in resp.json()["items"]:
        assert log["resource_type"] == "host"


def test_audit_acces_non_superuser(client, regular_auth_headers, auth_headers):
    """Non-superuser ne peut pas voir les logs → 403"""
    resp = client.get("/api/v1/audit-logs", headers=regular_auth_headers)
    assert resp.status_code == 403
