import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app  # Assuming `app` is the FastAPI instance
from app.api.endpoints import router  # Updated router import

# Add router to app for isolated testing
app.include_router(router)


@pytest.fixture
def client():
    """Fixture to create a FastAPI test client."""
    return TestClient(app)


@patch("app.core.state.ns")
def test_invite_node(mock_ns, client):
    """
    Test the /invite_node endpoint.
    """
    # Mock the ns object
    mock_ns.connector.get_connection.return_value = MagicMock(
        send_request=AsyncMock(return_value=MagicMock(status_code=200))
    )
    mock_ns.ring_nodes = {1: ("127.0.0.1", 8001)}

    response = client.post("/invite_node", json={"node_id": 2, "ip": "127.0.0.1", "port": 8002})

    assert response.status_code == 200
    assert response.json() == {"detail": "Success"}


@patch("app.core.state.ns")
@patch("app.api.endpoints.ring_transfer.AsyncClient")  # Updated namespace
def test_ring_transfer(mock_async_client, mock_ns, client):
    """
    Test the /ring_transfer endpoint.
    """
    mock_ns.connector.add_node = AsyncMock()
    mock_ns.manager.add_node = AsyncMock(return_value=["key1", "key2"])
    mock_ns.manager.get_value = MagicMock(return_value=("username", "/path/to/file"))
    mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=200)
    )

    response = client.post("/ring_transfer", json={"node_id": 2, "ip": "127.0.0.1", "port": 8002})

    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("app.core.state.ns")
def test_join_ring(mock_ns, client):
    """
    Test the /join_ring endpoint.
    """
    # Mock ns methods
    mock_ns.manager.reconstruct = MagicMock()
    mock_ns.initialize_connections = MagicMock()
    mock_ns.ring_nodes = {1: ("127.0.0.1", 8001), 2: ("127.0.0.1", 8002)}
    mock_ns.node_id = 1

    payload = {
        "node_data": {"nodes": {"2": {"ip": "127.0.0.1", "port": 8002}}},
        "ring_metadata": {"physical_nodes": {"2": 8002}},
    }
    response = client.post("/join_ring", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "success"