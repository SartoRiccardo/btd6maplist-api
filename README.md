# BTD6 Maplist API

Api for the BTD6 Maplist website and bot. Hosted at [apibtd6maplist.sarto.dev](https://apibtd6maplist.sarto.dev).

## Running locally

You will need a PostgreSQL database for this project, and initialize it with the queries in `database/schema.psql`; and a [Discord Application](https://discord.com/developers/applications) to run this project.

1. Clone the repo and install the project requirements
```bash
git clone https://github.com/SartoRiccardo/btd6maplist-api.git
cd btd6maplist-api
python -m pip install -r requirements.txt
```
2. Generate RSA keys for communication with [the bot](https://github.com/SartoRiccardo/btd6maplist-bot).
   - Only the public one is needed to check if the requests in bot routes are signed by the bot itself.
   - If you've already generated a key pair, simply move the public key here.
```bash
openssl genrsa -out btd6maplist-bot.pem 3072
openssl rsa -in btd6maplist-bot.pem -pubout -out btd6maplist-bot.pub.pem
```
3. Copy `config.example.py` into `config.py` and fill out the fields accordingly.
4. If using Docker, create a volume for either `PERSISTENT_DATA_PATH` or its contents:
   - `PERSISTENT_DATA_PATH/.cache` *(HTTP requests cache, optional)*
   - `PERSISTENT_DATA_PATH/logs`
   - `PERSISTENT_DATA_PATH/media`

## Bot Routes

Bot routes (marked in files named `bot.py` in the `api` folder) have close to no server-side authentication, this because there is no way for the server to get data directly from Discord, so the bot has to do it and verify it. Be very careful with these routes, make sure only the bot can access them.

Bot routes don't have Swagger documentation.

## Adding new routes

Simply create the route you wanna make in the `api` folder, and at the endpoint create the file `route.py`. There, you can define functions `get`, `post`, `put` or `delete`, which will be automatically added as routes. To create bot routes, the filename must be `bot.py` instead, and the suffix `/bot` will be appended to the route.
