# Bloons TD 6 Maplist API

You are working on the Bloons TD 6 Maplist API, a Python project built with a custom, handmade framework based on the `aiohttp` library. Below will be explained how to work with this project.

## Bloons TD 6 Maplist Framework

### Web Routes

Routes are dinamically made in the `api` folder. A route's path is, quite literally, the route's path. For example, `/api/users/{id}/route.py` translates to the route `/users/{id}`. Inside all of these folders goes the `route.py` file, which can define the methods `get`, `post`, `put`, `patch`, `delete`. These routes take the `aiohttp.web.Request` as a first parameter, and the other parameters (if any) are all dictated by middleware.

Middleware are all present in `src.utils.routedecos`. To apply them, simply decorate the function you wish to apply the middleware to. When using middleware, you should always add `**_kwargs` to the decorated function, in case you don't use all the arguments of the middleware, to prevent the function from erroring from receiving an unexpected parameter.

Route functions' docstrings are all swagger-compliant yaml. You can find model definitions in the docstrings of `src.db.models`. Inside this module, there are many dataclasses which, too, contain swagger-compliant yaml.

### Bot Routes

Some special routes, defined in `bot.py` instead of `route.py`, are defined as "Bot routes". These routes have the `/bot` suffix at the end of the route. Bot suffix should use a different type of authentication, based on signatures. If the signature is valid, then the request will be considered authenticated and the data from it is trustworthy (for example, if the payload says the request comes from a certain user, we can trust it as long as the signature is valid).

The special middleware that should **always** be included in bot routes is the `src.utils.routedecos.check_bot_signature` middleware.

### Queries

This project uses raw queries. Queries are made in the `src.db.queries` module, which includes lots of files categorized by purpose and/or model. The functions which define the queries always use the `src.db.connection.postgres` decorator, which injects a `conn: asyncpg.pool.PoolConnectionProxy` query parameter. You can assume this query parameter to be always valid (although in the function signature it should be initialized to None).

Functions in here should return either simple values or models, the latter of which are dataclasses defined in `src.db.models`. These dataclasses only store data and do not have methods that make queries. The only functions they may have are to manipulate the data they already have (for example, to convert itself to a dictionary to be returned from the API).

### Testing

Testing uses the `pytest` module. The tests go in the `test` folder and are divided semantically by type/purpose. Fixtures to generate data may use the `pytest_asyncio` fixture to properly handle resetting and the event loop. Tests should check behavior **from the point of view of the end user**, meaning we should never directly check database values (in fact, I have not coded such a function either)! When asserting, for example, that something was created successfully in the database, make a GET request to the resource and verify that every field corresponds to a determined pre-decided value. If the value cannot be determined (e.g. an ID), check its type and its existence and then unset it before performing a final check.

Common tests helpers include a data fuzzer, a data field "remover" (to test validation errors). You can find all sorts of helpers in the `tests.testutils` file.

### Migrations

Migrations are done through "patches" in the `database/patches` folder. You should name each patch `YYYY_MM_DD_HH_mm_ss-name.psql`. These files are pure SQL.

The `views.psql` and `triggers.psql` get called every time the API gets deployed, in that order. They are idempotent.

## Studying the code

You are **encouraged** to read other files in this project if you do not fully understand how something is done. It is a custom framework and you might not be used to how it works. Most of the files you will be working in are:

- The route files
- The query and model files
- The test files
- The migrations
