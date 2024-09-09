import os
import hashlib
import aiofiles
from config import PERSISTENT_DATA_PATH


media_path = os.path.join(PERSISTENT_DATA_PATH, "media")
os.makedirs(media_path, exist_ok=True)


async def save_media(
        media: bytes,
        ext: str,
        prefix: str = "",
        length: int = 50
) -> tuple[str, str]:
    fhash = hashlib.sha256(media).hexdigest()
    fname = f"{fhash}.{ext}"
    fpath = os.path.join(media_path, fname)
    async with aiofiles.open(fpath, "wb") as fout:
        await fout.write(media)
    return fname, fpath
