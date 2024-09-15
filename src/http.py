import aiohttp_client_cache
import cryptography.hazmat.primitives.asymmetric.rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key

http: aiohttp_client_cache.CachedSession
bot_pubkey: cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey | None = None


def set_session(pool: aiohttp_client_cache.CachedSession) -> None:
    global http
    http = pool


def set_bot_pubkey(keypath: str) -> None:
    global bot_pubkey
    with open(keypath, "rb") as fin:
        bot_pubkey = load_pem_public_key(fin.read())
