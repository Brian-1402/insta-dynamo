import os
import aiofiles
from fastapi import HTTPException
from app.core.config import STORE_DIR
from app.core.state import ns

os.makedirs(STORE_DIR, exist_ok=True)

async def save_file(file) -> str:
    file_path = os.path.join(STORE_DIR, file.filename)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(await file.read())
    return file_path

def get_valid_file_path(key: str) -> str:
    value = ns.manager.get_value(key)  # kv_storage should be pre-imported or globally available
    if not value:
        raise HTTPException(status_code=404, detail="Hash not found")
    file_path = value[1]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Hash found but file not found")
    return file_path