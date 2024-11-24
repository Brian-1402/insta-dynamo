import aiohttp
from aiohttp import ClientSession, FormData
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from db import SessionLocal, ImageKey, User
from crypto import encrypt_data, decrypt_data
import hashlib
import os
from io import BytesIO
import logging
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger("uvicorn.error")

image_router = APIRouter()

def get_db():
    try:
        db = SessionLocal()
        print("Database session created successfully")  # Debugging
        yield db
    except Exception as e:
        print(f"Database connection error: {e}")  # Log any connection errors
    finally:
        db.close()

IMAGE_SERVICE_IP = os.getenv("IMAGE_SERVICE_IP", "localhost")
IMAGE_SERVICE_PORT = os.getenv("IMAGE_SERVICE_PORT", "8000")
IMAGE_SERVICE_BASE_URL = f"http://{IMAGE_SERVICE_IP}:{IMAGE_SERVICE_PORT}"

def hash_key(key: str) -> int:
    """Generate a consistent hash for a given key."""
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)

async def store_image(user_id: int, username: str, image_file: UploadFile, db: Session):
    """
    Handles image processing, storage, and metadata insertion into the database.
    """
    # Read the raw image data
    raw_image_data = await image_file.read()

    # Compute the hash of the raw image to use as the key
    image_key = hash_key(raw_image_data.decode('latin1'))

    image_file.file.seek(0)  # Reset the pointer to the beginning of the file

    # Encrypt the image data
    encrypted_image_data = encrypt_data(raw_image_data)

    # Prepare the encrypted data as a file for the upload
    encrypted_file = BytesIO(encrypted_image_data)
    encrypted_file.seek(0)  # Reset the pointer to the beginning of the file

    connection = aiohttp.ClientSession(
            base_url=IMAGE_SERVICE_BASE_URL,
            timeout=aiohttp.ClientTimeout(total=10)
        )
    # Upload the encrypted file to the image storage service
    
    form = FormData()
    form.add_field("username", username)
    form.add_field("key", str(image_key))
    form.add_field(
        "file",
        filename=image_file.filename,
        value=image_file.file,
        content_type=image_file.content_type,
    )
    
    print(f"Uploading image with key: {image_key}")
    print(f"Form type: {type(form)}")
    print(f"Form fields: {form._fields}")
    print(f"form._fields[0]: {form._fields[0]}")
    print(f"form._fields[1]: {form._fields[1]}")
    print(f"form._fields[2]: {form._fields[2]}")

    async with connection.post(
        "/put_image",
        data=form
    ) as response:
        if response.status != 200:
            logger.error(f"Failed to upload image: {response.status} - {response.text}")
            raise HTTPException(status_code=500, detail="Failed to upload image")

    # Save metadata (image key) to the database
    db_image_key = ImageKey(id=user_id, username=username, image_key=image_key)
    db.add(db_image_key)
    db.commit()

    return image_key

async def retrieve_image(username: str, image_key: str):
    """
    Retrieves the encrypted image using the image storage service's `/get_image` endpoint.
    """
    connection = aiohttp.ClientSession(
        base_url=IMAGE_SERVICE_BASE_URL,
        timeout=aiohttp.ClientTimeout(total=10)
    )
    async with connection.get(f"/get_image", params={"username": username, "key": image_key}) as response:
        if response.status == 200:
            return await response.read()
        raise HTTPException(status_code=404, detail="Image not found")
    

@image_router.post("/upload")
async def upload_image(username: str = Form(...), image: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Handle image uploads and associate them with the logged-in user.
    """
    # Lookup user_id based on the username
    user = db.query(User).filter(User.username == username).first()
    # if not user:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User not found",
    #     )
    user_id = user.id

    image_key = await store_image(user_id=user_id, username=username, image_file=image, db=db)
    return {"message": "Image uploaded successfully", "key": image_key}

@image_router.get("/{key}")
async def get_image(username: str, key: str, db: Session = Depends(get_db)):
    # Verify the key exists in the database for the given user
    image_entry = db.query(ImageKey).filter(ImageKey.image_key == key, ImageKey.username == username).first()
    if not image_entry:
        raise HTTPException(status_code=404, detail="Image metadata not found")

    # Retrieve and decrypt the image from the storage service
    encrypted_image = await retrieve_image(username=username, image_key=key)
    decrypted_image = decrypt_data(encrypted_image)

    # Return the decrypted image (for now, as bytes)
    return {"image_data": decrypted_image.decode('latin1')}

@image_router.get("/list")
async def list_images(username: str, db: Session = Depends(get_db)):
    # Lookup user_id based on the username
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve all image keys associated with the user
    image_keys = db.query(ImageKey.image_key).filter(ImageKey.username == username).all()
    return {"images": [key for key, in image_keys]}
