# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

## Unreleased

## 0.1.0 - 2026-07-30

### Added

- Scalars: `int`, `float`, `string`, `bool`, `nil`, `any`, `some`, `uuid`, `keyword`, `symbol`, `re` (with `min`/`max` bounds where applicable).
- Composition: `and`, `or`, `enum`, `maybe`, `not`.
- Collections: `vector`, `sequential`, `set`, `tuple`, `map-of`.
- `map` with string keys, open-by-default, per-entry `optional`, and `{closed: true}` opt-in.
- `merge` — compose map schemas with last-value-wins.
- `multi` — dispatch by string discriminator; `missing-dispatch` / `invalid-dispatch` error tags.
- `explain` — structured errors with `path` (into schema) and `in` (into value).
- `humanize` — flat path-keyed dict of readable messages.
- `decode` / `parse` — coercion via transformers (`string_transformer`, `json_transformer`); `INVALID` sentinel.
- `register` / `register_composite` — public extension points.
