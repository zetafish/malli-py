# malli-py — Wiki

Internal knowledge doc for future sessions. Captures design, decisions, and where things live.

## What it is

Python port of Clojure's [malli](https://github.com/metosin/malli). Data-driven schemas: schemas are plain Python data (strings and lists), not classes. Built from scratch in this repo.

## Status

- 347 tests passing.
- Features shipped: scalars, composition (`and`/`or`/`enum`/`maybe`/`not`), collections (`vector`/`sequential`/`set`/`tuple`/`map-of`), `map` (open by default, per-entry optional, `{closed: true}`), `explain`, `humanize`, `decode` + `parse` + transformers, `merge`, `multi`.
- Not built (see "What's next").

## Layout

```
src/malli/
  __init__.py       -- public re-exports
  core.py           -- registries, _parse_schema, validate, explain, all scalars + composites
  humanize.py       -- explain result → path-keyed dict of readable messages
  decode.py         -- decode, parse, transformers, INVALID sentinel
tests/
  test_scalars.py       (70)
  test_composites.py    (34)
  test_collections.py   (64)
  test_map.py           (32)
  test_explain.py       (21)
  test_humanize.py      (32)
  test_decode.py        (46)
  test_merge.py         (20)
  test_multi.py         (28)
pyproject.toml      -- hatchling, src/ layout, Python ≥3.10, pytest as dev dep
mise.toml           -- Python 3.12, tasks: install/test/repl/clean
README.md           -- user-facing docs
WIKI.md             -- this file
```

## Core design

### Schemas are data

```python
"int"                                  -- bare string
["int", {"min": 0}]                    -- with props
["vector", "int"]                      -- with children
["map", ["name", "string"]]            -- entries as [key, schema] or [key, props, schema]
```

Rejected `":int"` (colon-prefixed) — user preferred plain strings.

### Two-tier registry (`core.py`)

- `_REGISTRY: dict[str, SimpleValidator]` — scalars. Signature `(value, props_or_arg) -> bool`.
- `_COMPOSITES: dict[str, (ValidateFn, ExplainFn)]` — everything that has children.

`register(name, fn)` and `register_composite(name, v, e)` are public.

### `_parse_schema(schema)` → `(name, props, children)`

Handles bare strings, `[name, props_dict, ...children]`, `[name, ...children]`. Raises `TypeError` on garbage.

### `validate` vs `_explain_impl`

- `validate(schema, value)` — returns bool. Composite lookup wins over scalar.
- `_explain_impl(schema, value, path, in_)` — returns list of error dicts. Wrapped by `explain` which returns `{value, schema, errors}` or `None`.

Error dict shape:
```
{"path": [...],   # index into schema
 "in":   [...],   # index into value
 "schema": ...,   # the failing schema
 "value": ...,    # the failing value
 "type": "..."}   # optional tag: missing-key, extra-key, missing-dispatch, invalid-dispatch
```

### `path` vs `in`

- `path` steps into the **schema** structure — child index or map key.
- `in` steps into the **value** — index for lists, key for dicts, actual element for sets (sets have no index).

`humanize` uses `in` for its keys because that's what users recognize.

### Scalars

`int`, `float`, `string` (all with `min`/`max` bounds), `bool`, `nil`, `any`, `some`, `uuid`, `keyword` (alias for `string`), `symbol` (alias for `string`), `re` (accepts both `["re", pattern]` and `["re", {"pattern": ...}]`).

**Footgun handled:** `isinstance(True, int) == True` in Python. `_v_int` explicitly rejects bool.

Regex uses `@lru_cache(maxsize=256)` on `_compile`.

### Composites

- `and` — all pass; explain collects all failures
- `or` — any passes; explain reports every branch if all fail
- `enum` — literal membership (uses `in children`)
- `maybe` — nil or child
- `not` — inverse of child
- `vector` — `list` only, size bounds
- `sequential` — `list` or `tuple`
- `set` — `set`/`frozenset`; error `in` uses the element (no index)
- `tuple` — fixed length; length mismatch is collection-level
- `map-of` — key errors path=[0], value errors path=[1], `in` is the key
- `map` — see below
- `merge` — resolves to a `:map`; later entries override earlier ones by key; top-level props shallow-merge with last-value-wins
- `multi` — dispatch by a string key in props; children are `[dispatch-value, schema]` pairs

### `map` details

- **String keys only** (per user choice).
- **Open by default**: extra keys ignored. `{"closed": true}` at the map level rejects extras.
- **Per-entry optional**: `["nickname", {"optional": True}, "string"]`.
- **Missing required** → error tagged `"missing-key"`, value `None`, schema = entry schema.
- **Extra on closed** → error tagged `"extra-key"`, schema = whole map schema, value = actual value.
- `_parse_map_entries` enforces shape, key type (str), and no duplicates.

### `merge` details

- Resolves to a `:map` at validate/explain/decode time via `_resolve_merge`.
- Later entries override earlier ones — both schema and per-entry props (so you can flip optional↔required by re-listing).
- Top-level map props (like `closed`) are shallow-merged with last-value-wins — but note: dict merge means an *absent* `closed` in the later map doesn't override a `true` from earlier. Documented in tests.
- Non-map child → `TypeError` at validate time. Empty children → `TypeError`.

### `multi` details

- Requires props `{"dispatch": <str>}`. Non-string dispatch → `TypeError`.
- Children: `[dispatch-value, schema]` pairs. Duplicate values → `TypeError`.
- Non-dict → collection-level error.
- Missing dispatch key → `"missing-dispatch"` tagged error, path/in appended with the key.
- Unknown dispatch value → `"invalid-dispatch"` tagged error.
- Match → delegates to child; branch errors bubble with unchanged path/in.

### `humanize` (humanize.py)

- Input: `explain` result (or None). Output: `dict[str, str]` (or None).
- Key: `_format_path(in_)` → dotted/bracketed path. Empty → `""`.
- Value: message dispatched on error `type` tag first (missing-key, extra-key, missing-dispatch, invalid-dispatch), else on schema name via `_MESSAGES` table.
- Key collision → join with `" and "` (deterministic, preserves signal from e.g. `:or`).
- Unknown schema name → `"invalid"` (no raise).
- No i18n / custom messages. Not nested — flat path-keyed dict is what forms want.

### `decode` / `parse` / transformers (decode.py)

- `decode(schema, value, transformer)` — walks schema; applies coercions per-node; leaves non-matching alone.
- `parse(schema, value, transformer=None)` — decode + validate; returns value or `INVALID` singleton (falsy, `is`-comparable, `repr == "INVALID"`).
- **Two transformers:**
  - `string_transformer` — string → int/float/bool/uuid; also `string` decoder that stringifies scalars.
  - `json_transformer` — list → set/tuple where schema calls for it; string → uuid.
- **Coercion is best-effort**: `_safe` wraps decoders so exceptions return the original value. Validation is a separate step.
- **Recurses into**: vector, sequential, set, tuple, map-of, map, merge (resolved), multi (matched branch).
- **Composites**: `maybe` unwraps None; `and` chains; `or` picks first branch whose decoded value validates; `enum`/`not` don't coerce.
- **No mutation**: dicts/lists are copied, not modified in place.

## Key design decisions (chronological)

1. **Data-first API**, not classes. Bare strings + lists.
2. **Reject `":int"` colon prefix** — user prefers plain names.
3. **`validate` only in first pass**, `explain` layered on top.
4. **Strings-only map keys**, open-by-default with `{closed: true}` opt-in, per-entry props for `optional`.
5. **Humanize output = flat path-keyed dict** (not nested), built-in messages only (no i18n).
6. **Decoding is best-effort, non-throwing**; validation is the gate.
7. **`or` decode strategy**: try each branch's decoder in order, pick first whose decoded value validates.
8. **`merge` shallow-merges top-level props** — documented gotcha: absent keys don't override present ones.
9. **`multi` uses string dispatch keys only** — parity with map string-keys-only policy.

## Testing conventions

- pytest, one file per feature (`test_<feature>.py`).
- Classes group related cases (`TestBasic`, `TestExplain`, `TestHumanize`, `TestDecode`, `TestNesting`).
- Use `parametrize` for repetitive negative cases.
- Every new feature adds tests for: basic pass/fail, explain output, humanize output, decode behavior, nesting inside/around existing features.

## Tooling

- **`mise`** pins the Python version and installs uv. Task runner (`mise run install/test/repl/typecheck/clean`). Run `mise trust` in project dir first.
- **`uv`** owns the venv (`.venv`), dependency resolution (`uv.lock`), and command execution (`uv run ...`). Replaced the prior pip-based workflow.
- Dev deps live in `[dependency-groups.dev]` (uv convention), not `[project.optional-dependencies]`.
- `uv.lock` is committed to git — reproducible installs across machines.
- Run tests with `uv run pytest` or `mise run test`.
- User's global CLAUDE.md mentions `clj-nrepl-eval` and `clj-paren-repair` — those are for Clojure work, not this repo. Ignore for malli-py.
- **Pre-commit hooks** (`.pre-commit-config.yaml`): trailing-whitespace/EOF/YAML/TOML hygiene, ruff (with `--fix`) + ruff-format, basedpyright. Pytest runs on `pre-push` only (keeps commits fast). Install with `pre-commit install && pre-commit install --hook-type pre-push`.
- **Versioning** via `hatch-vcs` — the version is derived from the latest `vX.Y.Z` git tag, written into `src/malli/_version.py` at build time, and re-exported as `malli.__version__`. `_version.py` is gitignored. `pyproject.toml` uses `dynamic = ["version"]` (no manual `version = "..."` line). Between tags, dev builds get a PEP 440 suffix like `0.1.1.dev3+g<sha>`; `local_scheme = "no-local-version"` strips the `+g<sha>` bit so PyPI accepts uploads.

## Releasing

1. Update `CHANGELOG.md`: move items from `## [Unreleased]` into a new `## [X.Y.Z] - YYYY-MM-DD` section. Update the link refs at the bottom.
2. `mise run release-check` — runs tests, typecheck, and sanity-checks the changelog.
3. Commit: `git commit -am "Release X.Y.Z"`.
4. Tag: `git tag vX.Y.Z` (the `v` prefix is what `hatch-vcs` expects).
5. Push: `git push && git push --tags`.
6. (Optional) `mise run build` produces sdist + wheel in `dist/` using the tag as the version. Not published anywhere yet.

`mise run version` prints what `hatch-vcs` currently infers — useful for a dry run.

## What's next (unbuilt)

Ranked by payoff:

1. **Temporal scalars** — `inst` (datetime), `date`, `local-date-time`. Small, unblocks real-world use at API boundaries.
2. **`encode`** — inverse of decode. Waits for temporal scalars; not much to encode today beyond UUID and set/tuple.
3. **`:ref` + schema registry** — needed for recursion (trees, mutual recursion) and better error messages. **Not needed for reuse** — plain Python variables handle that (`User = ["map", ..., ["email", Email]]` just works).
4. **`walk` / introspection API** — enables user tooling (doc generators, form builders).
5. **Generators** — Hypothesis-style value generation from schemas. Big surface.
6. **Function schemas (`:=>`)** — validate function args/returns. Niche in Python.
7. **`:seqex` (`:cat`, `:alt`, `:*`, `:+`, `:?`)** — regex sequence schemas. Rarely reached for.

## Things that are intentionally NOT in scope

- Nested humanize output (flat dict is what forms want).
- Custom humanize messages / i18n.
- Coercion that throws — errors surface at the validate step.
- Non-string map keys.
- Auto-detecting schema from value.
- Runtime type stubs / mypy plugin.

## Gotchas for future sessions

- **Don't confuse `path` and `in`.** `path` is into the schema (for tooling); `in` is into the value (for users).
- **`isinstance(True, int)` is True.** Any new numeric scalar must reject bool explicitly.
- **Sets have no index** — their error `in` uses the element itself.
- **`merge` shallow-merges props** — an absent `closed` in a later map doesn't unset a prior `closed: true`.
- **`multi` matched branch runs against the whole value**, not just the discriminator — the branch schema needs to include the discriminator field itself (see `Shape` in tests).
- **`_reconstruct(name, props, children)`** is the inverse of `_parse_schema` — use it when producing error `schema` fields so bare names round-trip as strings, not `["int"]`.
- **Decoder registration is via the transformer dict** — no side effects. Users bring their own transformer to `decode`/`parse`.
