import pytest
from app.core.hashring import HashRing

def test_hash_ring_initialization():
    nodes = ["node1", "node2", "node3"]
    ring = HashRing(nodes=nodes, vnodes=5, replicas=3)

    assert len(ring.physical_to_virtual) == len(nodes)
    for node in nodes:
        assert node in ring.physical_to_virtual
        assert len(ring.physical_to_virtual[node]) == 5


def test_add_node():
    ring = HashRing(vnodes=5)
    ring.add_node("node1")

    assert "node1" in ring.physical_to_virtual
    assert len(ring.physical_to_virtual["node1"]) == 5

    ring.add_node("node2", num_virtual_nodes=3)
    assert "node2" in ring.physical_to_virtual
    assert len(ring.physical_to_virtual["node2"]) == 3


def test_get_primary_node():
    nodes = ["node1", "node2", "node3"]
    ring = HashRing(nodes=nodes, vnodes=3)

    key = "some-key"
    primary_node = ring.get_primary_node(key)

    assert primary_node in nodes


def test_get_all_nodes():
    nodes = ["node1", "node2", "node3"]
    ring = HashRing(nodes=nodes, vnodes=5, replicas=3)

    key = "another-key"
    all_nodes = ring.get_all_nodes(key)

    assert len(all_nodes) == min(len(nodes), 3)
    assert len(set(all_nodes)) == len(all_nodes)  # Ensure nodes are unique


def test_get_all_nodes_capped_by_total_nodes():
    nodes = ["node1", "node2"]
    ring = HashRing(nodes=nodes, vnodes=5, replicas=5)

    key = "key-with-small-cluster"
    all_nodes = ring.get_all_nodes(key)

    assert len(all_nodes) == len(nodes)
    assert set(all_nodes) == set(nodes)


def test_list_virtual_nodes():
    ring = HashRing(vnodes=5)
    ring.add_node("node1")
    ring.add_node("node2")

    virtual_nodes_node1 = ring.list_virtual_nodes("node1")
    assert len(virtual_nodes_node1) == 5

    virtual_nodes_node2 = ring.list_virtual_nodes("node2")
    assert len(virtual_nodes_node2) == 5


def test_export_metadata():
    nodes = ["node1", "node2"]
    ring = HashRing(nodes=nodes, vnodes=5)

    metadata = ring.export_metadata()
    assert "physical_nodes" in metadata
    for node in nodes:
        assert metadata["physical_nodes"].get(node) == 5


def test_reconstruct_ring():
    nodes = ["node1", "node2"]
    ring = HashRing(nodes=nodes, vnodes=5)

    metadata = ring.export_metadata()
    new_ring = HashRing.reconstruct_ring(metadata, vnodes=5)

    assert len(new_ring.physical_to_virtual) == len(ring.physical_to_virtual)
    for node in nodes:
        assert node in new_ring.physical_to_virtual
        assert len(new_ring.physical_to_virtual[node]) == 5


def test_node_replicas_cap():
    # Ensure replicas do not exceed total nodes
    nodes = ["node1", "node2", "node3"]
    ring = HashRing(nodes=nodes, vnodes=5, replicas=5)

    key = "test-key"
    all_nodes = ring.get_all_nodes(key)

    assert len(all_nodes) == len(nodes)
    assert set(all_nodes) == set(nodes)

if __name__ == "__main__":
    pytest.main()