# Focused policy regression reference

## Trigger

Use when strengthening closeout/deploy-policy evidence in an existing focused pytest file, especially when production/config files are off-limits.

## Proven pattern

- Keep the change in the named test file only.
- Parse YAML with `yaml.safe_load` and exercise every configured channel/entry.
- Test semantic ordering rather than one exact prose spelling:
  - require `delegate_task`;
  - accept supported separators such as `Budget <= 15 phút, <= 15 tool calls` and `Budget <= 15 phút và <= 15 tool calls` with a narrow regex;
  - reject obsolete `<= 20 tool calls`;
  - require exactly one `Emergency Surgery L2` and check its position after the dispatch/budget clauses.
- Parse policy sections from Markdown and assert ordered labels/invariants. When headings differ in punctuation (for example `L2 (` rather than `L2:`), use a boundary-aware regex such as `^\\s*- (L[0-4])(?:\\s|:)` instead of overfitting to a colon.
- Exercise deployed guards through a subprocess JSON harness with synthetic payloads. Assert both block/allow behavior and meaningful message markers. Never execute the inspected ADB/closeout command.
- Keep each subprocess timeout bounded and run the focused canonical command after the final test edit.

## Failure lessons

A test that assumes one exact separator failed against a valid channel using a comma; adapt the assertion to the actual supported semantic variants, not by weakening the behavior being protected. A Markdown label assertion that required `L2:` failed because the real heading is `L2 (`; match the label boundary while still enforcing sequence.

## Evidence command

```text
python -m pytest D:/Taadaa/Hermes/tests/test_deploy_policy_rules.py -q -p no:cacheprovider
```

Report the exact pytest output and distinguish targeted evidence from a full-suite result. Do not commit, push, or run live closeout/device actions when the task excludes them.
