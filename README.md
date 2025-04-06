# BTD6 Maplist API - Test Branch

This is the branch for testing the website. This branch holds the special `/reset-test` route that resets the database with the test data.

In case for some reason this branch is not up-to-date with `main`, just merge it.

```bash
git checkout main-test
git merge main
```

In case in conflicts with the data in `/database/data`, only solve conflicts in `/database/data/gentestdata.py` and run the script again.
Note that the `/database/data` is not meant to seed data the API's tests, but the website's, so some data may differ.

## Usage

Simply create the route you wanna make in the `api` folder, and at the endpoint create the file `route.py`. There, you can define functions `get`, `post`, `put` or `delete`, which will be automatically added as routes. To create bot routes, the filename must be `bot.py` instead, and the suffix `/bot` will be appended to the route.

## Testing

To test the application, you must make a `config.test.py` where you override values in `config.py`. You don't have to put every config there, just the ones you want to override.
- You need an empty PostgreSQL database. The testing suite will automatically wipe and initialize it and use it.
- You need to create `tests/btd6maplist-bot.test.pem` with the method described above, for Bot Route tests.
