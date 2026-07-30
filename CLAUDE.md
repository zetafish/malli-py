# malli-py — instructions for Claude

## Read this first

**`WIKI.md` is the source of truth for this project's design, decisions, and current state.** Read it at the start of every session before doing anything non-trivial. It captures what's built, why, and gotchas that aren't obvious from the code.

## Keep the wiki current

Update `WIKI.md` whenever you:

- Ship a new feature (add it to "Status", update layout/test counts, add a section describing it).
- Make a design decision worth remembering (add to "Key design decisions" or "Gotchas").
- Discover a footgun or non-obvious behavior (add to "Gotchas").
- Remove or reshape something previously documented.
- Change what's next on the roadmap.

Don't wait to be asked. Treat wiki updates as part of shipping the change, same as tests and README.

Keep it terse — the wiki is for the next session's Claude, not marketing. Delete stale sections rather than piling on.

## Project conventions

- Schemas are plain Python data (strings and lists), not classes. No colon-prefixed names.
- Tests live in `tests/test_<feature>.py`, grouped by class, one file per feature.
- Every new feature needs tests for: basic pass/fail, `explain` output, `humanize` output, `decode` behavior, nesting.
- Update `README.md` (user-facing) and `WIKI.md` (internal) whenever the public surface changes.
- Use `.venv/bin/pytest` directly — `mise`-created venvs sometimes lack pip on PATH.
- Full test suite must pass before considering anything done.

## Style

- No comments unless the *why* is non-obvious.
- No docstrings on internal helpers.
- Prefer editing existing files over creating new ones.
- Don't add features, error handling, or abstractions beyond what the task requires.
