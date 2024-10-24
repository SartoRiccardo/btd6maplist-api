# BTD6 Maplist API - Test Branch

This is the branch for testing the website. This branch holds the special `/reset-test` route that resets the database with the test data.

In case for some reason this branch is not up-to-date with `main`, just merge it.
```bash
git checkout main-test
git merge main
```

## Usage

Compile `config.py` like you would normally in the `main` branch, and start it.
- You need an empty PostgreSQL database. The testing suit will automatically wipe and initialize it and use it.
