# Changelog

## 2025-05-06
### Added
- `/users/{uid}` supports a `minimal` query parameter to quickly get a minimal user's info. Useful for frontend.

### Changed
- LCC, No Geraldo, and Black Border leaderboards are now functions that take a format ID as a parameter instead of leaderboards.
  - Point leaderboards remain views
- Optimized a bunch of map-related queries!

## 2025-05-03
### Deleted
- `new_version` has been dropped from `map_list_meta`, `completions_meta`
  - Getting the current version now filters by `created_on` and picks the biggest value
