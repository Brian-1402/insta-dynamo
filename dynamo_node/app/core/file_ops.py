import os
import aiofiles
from fastapi import HTTPException
from app.core.config import STORE_DIR
from app.core.key_value import kv_storage

os.makedirs(STORE_DIR, exist_ok=True)

async def save_file(file) -> str:
    file_path = os.path.join(STORE_DIR, file.filename)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(await file.read())
    return file_path

def get_valid_file_path(key: str) -> str:
    file_path = kv_storage.get(key)  # kv_storage should be pre-imported or globally available
    if not file_path:
        raise HTTPException(status_code=404, detail="Hash not found")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Hash found but file not found")
    return file_path