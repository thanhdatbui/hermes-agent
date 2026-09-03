# ACCOUNT_READY anchor hook + post-hook transport boundary (2026-08-15)

Session-specific detail for the class-level `automation-core-consumer` skill.
It records the complete RED→GREEN→audit→one-live-run sequence and corrects the
earlier discovery note, which stopped before implementation.

## 1. Evidence that separated two failures

Fresh pre-hook run `follow-1-dcc073efdd4a`:

- Result: `MANUAL_REVIEW`, code `SWITCHER_ANCHOR_AMBIGUOUS`, `followed=[]`.
- Core timeline: verified Feed (20 nodes / 8835 B) → verified Profile (11 nodes /
  4794 B) → `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` → HTTP 502 /
  shell timeout.
- Final screen: ordinary Feed; switcher closed; retained dual lock.

Pinned core 0.4.44 already supports the optional adapter
`profile_identity(xml_text)` hook. Therefore the missing consumer seam was a
code issue, while the capture transport failures were a separate live-system
failure class.

## 2. Minimal implementation contract

Implement only this consumer hook:

```python
def profile_identity(self, xml_text: str | None = None) -> dict[str, str | bool]:
    from automation_core.tiktok.profile import profile_identity_from_xml

    empty = {"display_name": "", "username": "", "allow_generic_header": True}
    try:
        identity = profile_identity_from_xml(
            xml_text if xml_text is not None else self.dump_ui()
        )
    except Exception:
        return empty

    controls = {
        "sửa hồ sơ", "edit profile", "hồ sơ", "profile",
        "menu hồ sơ", "profile menu", "thêm tiểu sử", "add bio",
    }
    display_name = str(identity.get("display_name") or "").strip()
    username = str(identity.get("username") or "").strip()
    if display_name.casefold() in controls:
        display_name = ""
    if username and not username.startswith("@"):
        username = ""
    return {
        "display_name": display_name,
        "username": username,
        "allow_generic_header": True,
    }
```

Why this shape:

- Parsing stays in the public core API.
- Consumer exposes privacy-minimal identity only.
- Core retains ownership of `find_switcher_anchor`, semantic tap, selection,
  and verification.
- Missing/malformed identity remains fail-closed.
- No coordinate fallback, manual ADB tap, machine/account branch,
  `restart_profile_navigation`, `recover_ui_dump`, reboot, VPN, Search, Follow,
  or extra retry is introduced.

## 3. Required TDD proofs

Use fake identity values only:

1. Header identity is exposed and lets core `find_switcher_anchor` resolve the
   bounded header node.
2. Header-less XML returns empty identity and `find_switcher_anchor(...)` stays
   `None`.
3. `open_switcher(adapter, pre_confirmed_xml=..., attempts=1,
   load_attempts=1, settle_seconds=0)` opens the fake switcher using the hook;
   the only tap is the semantic anchor center chosen by core.

The first two tests were run RED before implementation (`AttributeError:
FollowAdapter has no attribute profile_identity`), then GREEN. Final exact tree:
`236 passed in 144.10s`; `py_compile` and `git diff --check` passed against the
pinned 0.4.44 wheel.

## 4. Exact-byte audit and retained-lock gate

Before the live retry:

- Build an audit prompt containing the exact current bytes, SHA-256 bindings,
  scoped diff, test evidence, and safety invariants.
- Run the independent AG auditor and require first-line verdict `APPROVED`.
  The implemented hook received APPROVED with no P0/P1.
- Read both retained aliases and prove they are the same blocked lease; prove
  old PID dead and no exact-target process.
- Never delete lock JSON directly. Acquire through core with authorized
  `FULL_SCOPE_TAKEOVER`, verify `takeover_from` and authorization in both
  aliases, then call `release_with_audit`.
- Require exactly two `released_paths` and both aliases absent before launch.

## 5. One materially-different run and the stopping boundary

Post-hook run `follow-1-3919760ab67d` was executed exactly once:

- Result: `MANUAL_REVIEW`, code `UI_DUMP_FAILED`, `followed=[]`.
- The prior `SWITCHER_ANCHOR_AMBIGUOUS` code did not recur.
- Artifacts again showed two verified captures (20 nodes / 8835 B, then 11
  nodes / 4794 B), followed by 30-second-deadline failures:
  `ADB_TRANSPORT_TIMEOUT`, HTTP 502, shell null-root, and shell timeout.
- Final screen was ordinary Feed; switcher closed; no OTP/CAPTCHA/permission/
  payment blocker; no target process; no success artifact.
- The new dual lease was retained `blocked`, `owner_active=false`.

Correct conclusion: the consumer hook fixed the missing semantic seam, but the
checkpoint still could not complete because the live UI-capture transport
failed. Do not relabel this as a failed hook, add more fallbacks, release the
new lock, or retry automatically. Preserve `followed=[]` and retained-handoff,
then wait for explicit operator review.

## 6. Durable pitfalls

- Match `%TEMP%/automation-core-ui-capture` artifacts to the exact run window;
  adjacent runs can have identical 20-node/11-node sequences.
- A successful early capture does not authorize using stale XML after a later
  transport loss. Fresh final identity recapture remains mandatory.
- A changed error code is progress evidence, not success evidence.
- Audit approval applies only to the exact hashes in its manifest; any edit
  afterward needs fresh verification/audit before another live run.
