# Deep-link transition audit recipe

Use this recipe for browser-to-app, email-link, OAuth, and other UI automation flows where a tap is expected to change application state.

## Evidence matrix

| Evidence | Proves | Does not prove |
|---|---|---|
| Semantic node / validated href found | The intended action was identified | The action was dispatched successfully |
| Target package foreground | The target app is visible | The deep-link payload was consumed |
| Post-action state classifier matches | The workflow reached the intended state | That every later caller is safe |

## Git-forensics commands

```bash
# Does the suspected symbol exist in the historical blobs?
for c in <old1> <old2> <old3> HEAD; do
  git show "$c:path/to/file.py" | python -c '... locate defs/callers ...'
done

# Find introduction/removal of a symbol or behavior
git log --all --oneline -S"symbol_or_literal" -- path/to/file.py

# Attribute exact lines to the introducing commit
git blame -L <start>,<end> <commit> -- path/to/file.py
```

Always distinguish committed history from an uncommitted working-tree addition. A current function absent from all historical blobs cannot be attributed to the named historical commits.

## Minimal patch heuristic

If a validated URL is available but a coordinate tap only brings the target app foreground, deliver that exact URL through the platform's native intent mechanism, then retain the strict postcondition verifier. Do not weaken the classifier to accept the unchanged pre-action screen. Separately report duplicate verification ownership in leaf and caller; remove it only after confirming which layer owns the contract.

## Concrete session pattern

In `Tiktok_Reg/social_reg_v1.py`, the Outlook reader had a CDP-validated `email_verification` href and a coordinate tap, while the app remained on the email-check screen. `_verify_visual_magic_link_transition` treated package presence as verified, but `_return_to_tiktok_after_magic_link` correctly classified the unchanged screen as `unknown`. The evidence supported an intent-delivery gap, not a reason to classify the email-check screen as success. The older branch's generic `here` tap and immediate `MAGIC_LINK` return were operationally permissive but not proof-safe.
