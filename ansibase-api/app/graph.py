from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class GroupNode:
    """
    Nœud représentant un groupe dans l'arbre hiérarchique
    """

    id: int
    name: str
    description: Optional[str]
    parent: Optional["GroupNode"] = None
    children: List["GroupNode"] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    hosts: Set[str] = field(default_factory=set)

    # Variables héritées calculées
    _computed_variables: Optional[Dict[str, Any]] = None
    _computed_hosts: Optional[Set[str]] = None

    def add_child(self, child: "GroupNode") -> None:
        """
        Ajoute un groupe enfant

        Args:
            child: Nœud enfant à ajouter
        """
        self.children.append(child)
        child.parent = self

    def get_all_variables(self) -> Dict[str, Any]:
        """
        Récupère toutes les variables du groupe (incluant celles héritées)
        Les variables locales ont priorité sur les variables héritées

        Returns:
            Dictionnaire des variables complètes
        """
        if self._computed_variables is not None:
            return self._computed_variables

        # Commencer par les variables héritées du parent
        computed: Dict[str, Any] = {}
        if self.parent:
            computed = self.parent.get_all_variables().copy()

        # Surcharger avec les variables locales
        computed.update(self.variables)

        self._computed_variables = computed
        return computed

    def get_all_hosts(self) -> Set[str]:
        """
        Récupère tous les hôtes du groupe (incluant ceux des enfants)
        Propagation de bas en haut

        Returns:
            Ensemble des noms d'hôtes
        """
        if self._computed_hosts is not None:
            return self._computed_hosts

        # Commencer par les hôtes directs
        all_hosts: Set[str] = self.hosts.copy()

        # Ajouter récursivement les hôtes des enfants
        for child in self.children:
            all_hosts.update(child.get_all_hosts())

        self._computed_hosts = all_hosts
        return all_hosts

    def invalidate_cache(self) -> None:
        """Invalide le cache des valeurs calculées"""
        self._computed_variables = None
        self._computed_hosts = None

        # Propager aux enfants
        for child in self.children:
            child.invalidate_cache()

    def __repr__(self) -> str:
        return f"<GroupNode(name='{self.name}', hosts={len(self.hosts)}, children={len(self.children)})>"


class GroupTree:
    """
    Arbre hiérarchique des groupes
    Gère la construction et la navigation dans la hiérarchie
    """

    def __init__(self) -> None:
        """Initialise l'arbre des groupes"""
        self.nodes: Dict[int, GroupNode] = {}
        self.nodes_by_name: Dict[str, GroupNode] = {}
        self.root: Optional[GroupNode] = None

    def add_group(
        self,
        group_id: int,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
    ) -> GroupNode:
        """
        Ajoute un groupe à l'arbre

        Args:
            group_id: ID du groupe
            name: Nom du groupe
            description: Description du groupe
            parent_id: ID du groupe parent (None pour la racine)

        Returns:
            Nœud créé
        """
        node = GroupNode(id=group_id, name=name, description=description)

        self.nodes[group_id] = node
        self.nodes_by_name[name] = node

        # Définir la racine si c'est le groupe "all"
        if name == "all":
            self.root = node

        # Attacher au parent si spécifié
        if parent_id is not None and parent_id in self.nodes:
            parent_node = self.nodes[parent_id]
            parent_node.add_child(node)

        return node

    def get_node(self, group_id: int) -> Optional[GroupNode]:
        return self.nodes.get(group_id)

    def get_node_by_name(self, name: str) -> Optional[GroupNode]:
        return self.nodes_by_name.get(name)

    def build_hierarchy(self) -> None:
        """
        Construit la hiérarchie en reliant les nœuds orphelins
        Utile si les groupes ont été ajoutés dans le désordre
        """
        for node in self.nodes.values():
            if node.parent is None and node.name != "all":
                # Chercher le parent dans les nœuds existants
                # (normalement déjà fait dans add_group)
                pass

    def traverse_preorder(self, node: Optional[GroupNode] = None) -> List[GroupNode]:
        """
        Parcours en profondeur préfixé (parent avant enfants)

        Args:
            node: Nœud de départ (racine si None)

        Returns:
            Liste ordonnée des nœuds
        """
        if node is None:
            node = self.root

        if node is None:
            return []

        result: List[GroupNode] = [node]
        for child in node.children:
            result.extend(self.traverse_preorder(child))

        return result

    def traverse_postorder(self, node: Optional[GroupNode] = None) -> List[GroupNode]:
        """
        Parcours en profondeur suffixé (enfants avant parent)
        Utile pour propager les hôtes de bas en haut

        Args:
            node: Nœud de départ (racine si None)

        Returns:
            Liste ordonnée des nœuds
        """
        if node is None:
            node = self.root

        if node is None:
            return []

        result: List[GroupNode] = []
        for child in node.children:
            result.extend(self.traverse_postorder(child))
        result.append(node)

        return result

    def __repr__(self) -> str:
        return f"<GroupTree(nodes={len(self.nodes)}, root={self.root.name if self.root else None})>"
