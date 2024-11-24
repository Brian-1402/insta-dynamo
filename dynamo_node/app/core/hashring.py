from sortedcontainers import SortedDict
from collections import defaultdict
import hashlib
from typing import Callable, Optional, List


class HashRing:
    """
    Implements consistent hashing with support for virtual nodes and replicas using SortedDict.

    - Nodes (physical and virtual) are hashed and stored in a sorted dictionary.
    - Keys are assigned to the closest node in the ring (primary node) and replicated across
      multiple unique physical nodes.
    - Supports addition of new physical nodes, retrieval of primary node for a key,
      retrieval of all nodes for a key, and listing virtual nodes of a physical node.
    """

    def __init__(
        self,
        nodes: List[str] = [],
        hash_fn: Optional[Callable[[str], int]] = None,
        vnodes: int = 5,
        replicas: int = 3,
    ):
        self.ring = SortedDict()  # Maps virtual node hashes to physical node IDs
        self.physical_to_virtual = defaultdict(list)
        self.vnodes = vnodes
        self.replicas = replicas
        self._hash = self._hash_default
        if hash_fn:
            self._hash = hash_fn
        if nodes:
            for node in nodes:
                self.add_node(node)

    @staticmethod
    def _hash_default(value: str) -> int:
        return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)

    def add_node(self, physical_node_id: str, num_virtual_nodes: Optional[int] = None):
        """
        Adds a physical node with its virtual nodes to the hash ring.

        Args:
            physical_node_id (str): Unique identifier for the physical node.
            num_virtual_nodes (int): (Optional) Number of virtual nodes to create for this physical node.
        """
        if num_virtual_nodes is None:
            num_virtual_nodes = self.vnodes
        for i in range(num_virtual_nodes):
            virtual_node_id = f"{physical_node_id}-vn{i}"
            virtual_hash = self._hash(virtual_node_id)
            if virtual_hash not in self.ring:
                self.ring[virtual_hash] = physical_node_id
                self.physical_to_virtual[physical_node_id].append(virtual_hash)

    def get_primary_node(self, key: str) -> str:
        """
        Finds the primary node responsible for a given key.

        Args:
            key (str): The key to locate in the hash ring.

        Returns:
            str: The primary physical node ID responsible for the key.
        """
        key_hash = self._hash(key)
        idx = self.ring.bisect_right(key_hash)
        if idx == len(self.ring):  # Wrap around to the beginning of the ring
            idx = 0
        return self.ring[list(self.ring.keys())[idx]]

    def get_all_nodes(self, key: str) -> list[str]:
        """
        Retrieves all nodes (primary + replicas) for a given key.

        Args:
            key (str): The key to locate in the hash ring.

        Returns:
            list[str]: List of physical node IDs responsible for the key.
        """
        key_hash = self._hash(key)
        idx = self.ring.bisect_right(key_hash)
        if idx == len(self.ring):  # Wrap around to the beginning of the ring
            idx = 0

        seen_nodes = set()
        nodes = []

        for _ in range(len(self.ring)):
            virtual_hash = list(self.ring.keys())[idx]
            # virtual_hash = self.ring.keys[idx]
            physical_node = self.ring[virtual_hash]
            if physical_node not in seen_nodes:
                nodes.append(physical_node)
                seen_nodes.add(physical_node)
                if len(nodes) == self.replicas:
                    break
            idx = (idx + 1) % len(self.ring)

        return nodes

    def list_virtual_nodes(self, physical_node_id: str) -> list[str]:
        """
        Lists all virtual node hashes for a given physical node.

        Args:
            physical_node_id (str): Physical node ID to query.

        Returns:
            list[str]: List of virtual node hash values for the given physical node.
        """
        # idx = self.ring.index(self._hash(physical_node_id)) 
        # return [self.ring.iloc(idx)]
        return self.physical_to_virtual[physical_node_id]
        # return [self.ring.keys(self.ring.index(physical_node_id))]

    def export_metadata(self) -> dict:
        """
        Exports the metadata of the hash ring, which includes physical nodes
        and the number of virtual nodes for each physical node.

        Returns:
            dict: Metadata dictionary containing the physical nodes and their virtual node count.
        """
        return {
            "physical_nodes": {
                node: len(self.physical_to_virtual[node]) for node in self.physical_to_virtual
            }
        }
        

    @classmethod
    def reconstruct_ring(cls, metadata: dict, vnodes: int = 5, replicas: int = 3) -> "HashRing":
        """
        Reconstructs a HashRing instance from the exported metadata.

        Args:
            metadata (dict): Metadata dictionary containing physical nodes and their virtual node counts.
            vnodes (int): Default number of virtual nodes if not specified in metadata.
            replicas (int): Default number of replicas if not specified in metadata.

        Returns:
            HashRing: A reconstructed HashRing instance.
        """
        hash_ring = cls(vnodes=vnodes, replicas=replicas)
        for physical_node, num_virtual_nodes in metadata["physical_nodes"].items():
            hash_ring.add_node(physical_node, num_virtual_nodes)
        return hash_ring