import io
import os
import hashlib
import aiofiles
from config import PERSISTENT_DATA_PATH
from PIL import Image


media_path = os.path.join(PERSISTENT_DATA_PATH, "media")
os.makedirs(media_path, exist_ok=True)


async def save_media(
        media: bytes,
        ext: str,
) -> tuple[str, str]:
    fhash = hashlib.sha256(media).hexdigest()
    fname = f"{fhash}.{ext}"
    fpath = os.path.join(media_path, fname)
    async with aiofiles.open(fpath, "wb") as fout:
        await fout.write(media)
    return fname, fpath


async def save_image(
        media: bytes,
        ext: str,
) -> tuple[str, str]:
    fhash = hashlib.sha256(media).hexdigest()
    if ext.lower() in ["png", "jpg", "jpeg"]:
        image = Image.open(io.BytesIO(media))
        media_io = io.BytesIO()
        ext = "webp"
        image.save(media_io, format=ext)
        media = media_io.getvalue()

    fname = f"{fhash}.{ext}"
    fpath = os.path.join(media_path, fname)
    if not os.path.exists(fpath):
        async with aiofiles.open(fpath, "wb") as fout:
            await fout.write(media)
    return fname, fpath
