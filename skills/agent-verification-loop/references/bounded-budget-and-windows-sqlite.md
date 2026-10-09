# Bounded-budget investigations and Windows SQLite fixtures

## Why this reference exists

Use this when a repository task has a strict call/time budget and a focused
mocked regression test on Windows.

## Investigation gate

Before editing, use the first few calls to establish four anchors:

1. the exact target function and the early-return/data-flow defect;
2. every current caller and the actual argument/data shapes at the boundary;
3. one existing focused test file that can be extended without adding a new
   test surface;
4. the relevant case/documentation entry, using bounded path/file searches.

Do not start speculative production edits or broad searches before this
compatibility check. If the requested contract cannot be implemented safely in
the remaining budget, abort early and report the concrete function/call-site
anchor plus the proposed backward-compatible contract. A partial source patch
is not useful evidence.

For a scope allowing one production file and at most one existing test file,
keep all edits inside those two paths. Do not add fixtures, helpers, docs, or
cleanup files unless explicitly authorized.

## Windows SQLite regression-fixture rule

`NamedTemporaryFile` commonly remains open on Windows. Opening that same path
with `sqlite3.connect()` can fail with:

```text
sqlite3.OperationalError: unable to open database file
```

This is a harness setup failure, not a RED result for the production bug. Use a
`TemporaryDirectory()` and construct a database path, or close the temporary
file before opening SQLite. Then rerun until the test reaches the intended
production seam/assertion.

Example:

```python
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = os.path.join(tmpdir, "tracker.db")
    conn = sqlite3.connect(db_path)
```

Classify pre-test fixture exceptions as `HARNESS_SETUP_FAILURE`; do not weaken
the regression assertion or report them as production failures.
