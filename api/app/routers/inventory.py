"""
Router pour l'export d'inventaire Ansible
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services import inventory as inventory_service
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


# ── Export inventaire complet


@router.get("")
def export_inventory(
    # corps, parametres de la requete
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = inventory_service.build_inventory(db)

    log_action(
        db,
        user_id=current_user.id,
        action="EXPORT",
        resource_type="inventory",
        details={"type": "full"},
        ip_address=request.client.host if request.client else None,
    )
    return result


# ── Variables d'un hôte


@router.get("/hosts/{hostname}")
def get_host_vars(
    # corps, parametres de la requete
    hostname: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = inventory_service.get_host_vars(db, hostname)

    log_action(
        db,
        user_id=current_user.id,
        action="EXPORT",
        resource_type="inventory",
        details={"type": "host_vars", "hostname": hostname},
        ip_address=request.client.host if request.client else None,
    )
    return result


# ── Graphe des groupes


@router.get("/graph")
def inventory_graph(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return inventory_service.build_graph(db)
