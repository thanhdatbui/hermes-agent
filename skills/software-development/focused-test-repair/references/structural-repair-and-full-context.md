# Structural Repair and Full-Context Acceptance Checklist

Use this checklist when a delegated worker reports a malformed focused test or a
provider route changes from bounded rejection to unlimited full-context send.

## Structural anchors

- Parse/compile the live test file before editing.
- Search for duplicate test names and stale production constant references.
- If a body is orphaned after a previous test, restore its `def` line immediately
  above the existing body; retain its assertions unless the contract changed.
- Confirm exactly one definition remains for each named regression.

## Full-context regression shape

```python
client.session.post = MagicMock(return_value=mock_response)
large_diff = "diff header\n" + ("+payload\n" * 600 * 1024) + "FULL_DIFF_TAIL"
meta = {}
client._post_full_context(
    "system", "", EXACT_TERRA_MODEL, large_diff, "", meta
)
posted = json.loads(client.session.post.call_args.kwargs["data"].decode("utf-8"))
assert posted["model"] == EXACT_TERRA_MODEL
assert meta["truncated"] is False
assert "FULL_DIFF_TAIL" in posted["messages"][1]["content"]
client.session.post.assert_called_once()
```

Use a single large fixture, not repeated large allocations. If the provider mock
returns a structured response, make it valid enough for the production response
path to complete. Keep the exact-model bypass test separate from the large-payload
acceptance test.

## Final evidence

After the last source or test edit, run the exact user-mandated focused pytest
command. Then run the requested `py_compile` and `git diff --check` commands.
Report any missing structural anchor or unrun command plainly; a partial patch is
not a verified completion.