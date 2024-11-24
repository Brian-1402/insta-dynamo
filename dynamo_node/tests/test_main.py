import pytest
from fastapi.testclient import TestClient
from hashlib import sha256
from app.main import app
import os

from app.core.hashmanager import DistributedKeyValueManager

NODE_ID = "node1"
VNODES = 5
N_REPLICAS = 3
STORE_DIR = "./store"

client = TestClient(app)

@pytest.fixture
def manager():
    """Fixture to initialize a DistributedKeyValueManager."""
    return DistributedKeyValueManager(nodes=[], node_id=NODE_ID, vnodes=VNODES, replicas=N_REPLICAS)

def setup_function(manager):
    """Setup function to reset the hash table and ensure a clean store directory."""
    if os.path.exists(STORE_DIR):
        for file in os.listdir(STORE_DIR):
            os.remove(os.path.join(STORE_DIR, file))

def teardown_function(manager):
    """Cleanup function after tests."""
    setup_function(manager)

def test_upload_image(manager):
    """Test the image upload functionality."""
    image_path = "test_image.jpg"
    with open(image_path, "wb") as f:
        f.write(os.urandom(1024))  # Write random data to simulate an image

    with open(image_path, "rb") as f:
        file_contents = f.read()
        hash_value = sha256(file_contents).hexdigest()

    response = client.post(
        "/upload",
        data={"username": "testuser", "key": hash_value},
        files={"file": ("test_image.jpg", open(image_path, "rb"), "image/jpeg")},
    )
    os.remove(image_path)

    assert response.status_code == 200
    assert response.json()["key"] == hash_value
    assert response.json()["filename"] == "test_image.jpg"
    assert response.json()["username"] == "testuser"

def test_fetch_image(manager):
    """Test the image fetch functionality."""
    # Upload an image
    image_path = "test_image.jpg"
    with open(image_path, "wb") as f:
        f.write(os.urandom(1024))  # Write random data to simulate an image

    with open(image_path, "rb") as f:
        file_contents = f.read()
        hash_value = sha256(file_contents).hexdigest()

    client.post(
        "/upload",
        data={"username": "testuser", "key": hash_value},
        files={"file": ("test_image.jpg", open(image_path, "rb"), "image/jpeg")},
    )

    # Fetch the uploaded image
    response = client.get(f"/fetch/{hash_value}")
    os.remove(image_path)

    assert response.status_code == 200
    assert response.content == file_contents

def test_fetch_nonexistent_hash(manager):
    """Test fetching an image with a nonexistent hash."""
    response = client.get("/fetch/nonexistenthash")
    assert response.status_code == 404
    assert response.json()["detail"] == "Hash not found"
