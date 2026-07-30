# malli-py

A Python port of [Clojure's malli](https://github.com/metosin/malli) — data-driven schemas for validation, coercion, and human-readable errors.

Schemas are plain Python data (strings and lists), not classes:

```python
import malli as m

m.validate("int", 42)                       # True
m.validate(["int", {"min": 0}], -1)         # False
m.validate(["vector", "string"], ["a"])     # True
```

## Install

```bash
pip install -e ".[dev]"
```

Or with [mise](https://mise.jdx.dev/):

```bash
mise run install
```

## Test

```bash
mise run test        # or: pytest
```

## Features

### Scalars

`int`, `float`, `string`, `bool`, `nil`, `any`, `some`, `uuid`, `keyword`, `symbol`, `re`.

Bounded variants take a props dict:

```python
m.validate(["int", {"min": 0, "max": 100}], 50)          # True
m.validate(["string", {"min": 1, "max": 10}], "hi")      # True
m.validate(["re", r"^\d+$"], "123")                       # True
```

### Composition

`and`, `or`, `enum`, `maybe`, `not`.

```python
m.validate(["and", "int", ["int", {"min": 0}]], 5)       # True
m.validate(["or", "int", "string"], "hi")                # True
m.validate(["enum", "red", "green", "blue"], "red")      # True
m.validate(["maybe", "int"], None)                       # True
m.validate(["not", "int"], "hi")                         # True
```

### Collections

`vector`, `sequential`, `set`, `tuple`, `map-of`.

```python
m.validate(["vector", "int"], [1, 2, 3])                 # True
m.validate(["set", "string"], {"a", "b"})                # True
m.validate(["tuple", "int", "string"], [1, "hi"])        # True
m.validate(["map-of", "string", "int"], {"a": 1})        # True
```

### Maps

Open by default (extra keys allowed); string keys only; `{"optional": True}` marks per-entry optional; `{"closed": True}` at the map level forbids extras.

```python
User = [
    "map",
    ["name", "string"],
    ["age", ["int", {"min": 0}]],
    ["nickname", {"optional": True}, "string"],
]
m.validate(User, {"name": "Ada", "age": 42})                    # True
m.validate(User, {"name": "Ada", "age": 42, "extra": 1})        # True (open)

Closed = ["map", {"closed": True}, ["name", "string"]]
m.validate(Closed, {"name": "Ada", "x": 1})                     # False
```

### `explain`

Structured errors, with `path` (into schema) and `in` (into value):

```python
m.explain(User, {"age": -1})
# {
#   "value": {"age": -1},
#   "schema": [...],
#   "errors": [
#     {"path": ["name"], "in": ["name"], "schema": "string",
#      "value": None, "type": "missing-key"},
#     {"path": ["age"], "in": ["age"], "schema": ["int", {"min": 0}],
#      "value": -1},
#   ]
# }
```

Returns `None` when the value is valid.

### `humanize`

Turns an `explain` result into a flat path-keyed dict of readable messages:

```python
m.humanize(m.explain(User, {"age": -1}))
# {"name": "missing required key", "age": "should be an int at least 0"}

m.humanize(m.explain(["vector", "int"], [1, "x", 3]))
# {"[1]": "should be an int"}

m.humanize(m.explain(
    ["map", ["users", ["vector", ["map", ["name", "string"]]]]],
    {"users": [{"name": "Ada"}, {"name": 3}]},
))
# {"users[1].name": "should be a string"}
```

### `decode` and `parse` — coercion

`decode` walks a schema and coerces values via a transformer. Non-matching inputs are left alone (validation is a separate step).

```python
m.decode("int", "42", m.string_transformer)             # 42
m.decode("bool", "true", m.string_transformer)          # True
m.decode(["vector", "int"], ["1", "2"], m.string_transformer)  # [1, 2]

User = ["map", ["name", "string"], ["age", "int"]]
m.decode(User, {"name": "Ada", "age": "42"}, m.string_transformer)
# {"name": "Ada", "age": 42}
```

Two built-in transformers:

- `string_transformer` — parses strings into `int`, `float`, `bool`, `uuid`.
- `json_transformer` — post-JSON coercions: lists → `set`/`tuple` where the schema calls for it, strings → `uuid`.

`parse` combines decode + validate, returning the value on success or the `INVALID` sentinel on failure:

```python
m.parse("int", "42", m.string_transformer)     # 42
m.parse("int", "abc", m.string_transformer)    # INVALID
if (v := m.parse(schema, raw, m.string_transformer)) is not m.INVALID:
    ...
```

### Custom schemas

```python
m.register("even", lambda v, _p: isinstance(v, int) and v % 2 == 0)
m.validate("even", 4)   # True
```
