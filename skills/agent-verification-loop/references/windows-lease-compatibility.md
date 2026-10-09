# Windows lease compatibility

## Reproduction

A filesystem-backed lease registry can fail in two separate ways on Windows:

1. `os.path.normcase()` lowercases the canonical identity key, so persisting that key changes the caller-visible path (`D:/Taadaa` becomes `d:/taadaa`).
2. A stored record created through one case/alias may not compare equal to a later canonical request, causing an expired record to be treated as corrupt and preventing guarded takeover.

Focused regression shape:

```python
old = registry.acquire(
    "D:/Taadaa/tools/a.py", "session-a", "owner-a", "base-a", ttl_seconds=0.01
)
time.sleep(0.03)
assert registry.acquire("D:/Taadaa/tools/a.py", "session-b", "owner-b", "base-b").code == "LEASE_EXPIRED"
replacement = registry.takeover_guarded(
    "D:/Taadaa/tools/a.py", "session-b", "owner-b", "base-b",
    expected_lease_id=old.lease_id,
)
assert replacement.ok and replacement.lease_id != old.lease_id
```

Also assert that the persisted `record.path` is the normalized absolute display path, while aliases still collide through the canonical key.

## Implementation pattern

Keep two representations:

- **Canonical key:** absolute + normalized + `normcase` + slash-normalized. Use it for record filenames, lock filenames, locks, and identity comparisons.
- **Display path:** normalized absolute path without `normcase`, slash-normalized. Persist it in `LeaseRecord.path` for compatibility.

When reading a record, compare `_path_key(existing.path)` to the requested canonical key. For renewal/release, lock using the canonicalized record path. Guarded takeover must perform the expiry and expected-ID checks inside the per-path lock, then publish the replacement atomically.

On Windows, opening a replaced file as `rb` may not provide a suitable descriptor for `fsync`; use `r+b` for the post-`os.replace` fsync step.

## Verification

Run the smallest focused module after the final edit:

```bash
python -m py_compile session_lease.py
python -m pytest -q -p no:cacheprovider tests/test_session_lease.py
git diff --check -- session_lease.py tests/test_session_lease.py
```

Do not claim a full-suite pass from this focused evidence. Preserve unrelated dirty or untracked test files.
