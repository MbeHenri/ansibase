"""
Dépendance de pagination pour les endpoints de liste
"""

from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    """Paramètres de pagination extraits des query params"""

    page: int = Query(default=1, ge=1, description="Numéro de page")
    per_page: int = Query(default=50, ge=1, le=100, description="Éléments par page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page
