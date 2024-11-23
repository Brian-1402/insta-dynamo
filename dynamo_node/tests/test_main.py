import pytest
from fastapi.testclient import TestClient
from hashlib import sha256
from app.main import app
from app.core.key_value import kv_storage
from app.core.config import STORE_DIR
import os


client = TestClient(app)

def setup_function():
    """Setup function to reset the hash table and ensure a clean store directory."""
    global hash_table
    kv_storage.clear()
    if os.path.exists(STORE_DIR):
        for file in os.listdir(STORE_DIR):
            os.remove(os.path.join(STORE_DIR, file))

def teardown_function():
    """Cleanup function after tests."""
    setup_function()

def test_upload_image():
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

def test_fetch_image():
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

def test_fetch_nonexistent_hash():
    """Test fetching an image with a nonexistent hash."""
    response = client.get("/fetch/nonexistenthash")
    assert response.status_code == 404
    assert response.json()["detail"] == "Hash not found"
