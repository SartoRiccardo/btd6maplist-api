import os
import random
import string
import aiofiles
from config import PERSISTENT_DATA_PATH


media_path = os.path.join(PERSISTENT_DATA_PATH, "media")
os.makedirs(media_path, exist_ok=True)


async def save_media(media: bytes, ext: str) -> tuple[str, str]:
    randstr = "".join(random.choices(string.ascii_letters+string.digits, k=50))
    fname = f"{randstr}.{ext}"
    fpath = os.path.join(media_path, fname)
    async with aiofiles.open(fpath, "wb") as fout:
        await fout.write(media)
    return fname, fpath
