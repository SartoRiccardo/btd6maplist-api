import os.path

APP_HOST = "localhost"
APP_PORT = 4000

PERSISTENT_DATA_PATH = os.path.expanduser("~")
WEB_BASE_URL = "https://localhost:3000"
MEDIA_BASE_URL = "https://localhost:5000"
# Discord doesn't embed URLs with a file extension, and NK's map preview urls don't have one. Proxy it somehow.
NK_PREVIEW_PROXY = lambda code: f"http://localhost:5000/map/{code}.jpg"

DB_USER = "postgres"
DB_PSWD = "postgres"
DB_HOST = "127.0.0.1"
DB_NAME = "database"

BOT_PUBKEY = "btd6maplist-bot.pub.pem"
BOT_TOKEN = "bot-token.jwt"
BOT_UA = "DiscordBot (https://localhost:3000, 1.0)"

CORS_ORIGINS = ["*"]
