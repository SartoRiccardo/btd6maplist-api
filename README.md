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

Compile `config.py` like you would normally in the `main` branch, and start it. `config.test.py` can also be compiled to override some variables in `config.py`, should you want to.
- You need an empty PostgreSQL database. The testing suit will automatically wipe and initialize it and use it.
