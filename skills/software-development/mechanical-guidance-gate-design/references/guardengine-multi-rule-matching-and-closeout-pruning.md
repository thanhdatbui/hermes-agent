# GuardEngine Multi-Rule Matching & Closeout Scope Pruning

## 1. Problem Statement
Two severe structural flaws were discovered in the gate enforcement architecture:

### Issue A: Rule Shadowing in GuardEngine
`GuardEngine._match_rule(action)` previously iterated through configured rules and returned the **first** rule where `match["tool_class"] == tool_class and match["op"] == op`:
```python
def _match_rule(self, action: Mapping[str, Any]) -> dict[str, Any] | None:
    tool_class = action.get("tool_class")
    op = action.get("op")
    for rule in self._rules:
        if rule["match"]["tool_class"] == tool_class and rule["match"]["op"] == op:
            return rule
    return None
```
In `rules.json`, multiple invariant rules (`case_162_usb_micro_drop_timeout_floor`, `case_161_natural_follow_limit_ceiling`, `dispatch_worker_timeout_floor`) all declare `match: {"tool_class": "code_edit", "op": "commit"}`. Because `_match_rule` stopped at the first match (`case_162`), all subsequent rules were **completely ignored and shadowed**. A diff violating `case_161` (`follow_limit = 5`) was evaluated only against `case_162`, found no USB timeout changes, and returned `STATUS: ALLOW`!

### Issue B: Closeout Gate Step 2 Crash on Unchanged Targets
In `closeout_gate.py` (`targeted_candidate` function):
```python
if changed:
    if sorted(changed) != targets:
        raise ValueError(f"targets without working-tree changes: {sorted(set(targets) - changed)}")
    return "worktree_targeted", targets, diff
```
When an operator or coordinator ran `closeout_gate.py --files A B C` where file `C` had already been committed or had no uncommitted diff, the script threw `ValueError` and exited with error code 1, completely crashing the evaluation pipeline instead of pruning unchanged files and evaluating the diff of files that actually changed.

---

## 2. Structural Fixes

### Fix A: Multi-Rule Matching in `GuardEngine` (`engine.py`)
Replaced `_match_rule` with `_match_rules`:
```python
def _match_rules(self, action: Mapping[str, Any]) -> list[dict[str, Any]]:
    tool_class = action.get("tool_class")
    op = action.get("op")
    return [
        rule for rule in self._rules
        if rule["match"]["tool_class"] == tool_class and rule["match"]["op"] == op
    ]
```
In `_decide(action)`:
1. Fetch all `matching_rules = self._match_rules(action)`.
2. Iterate through each rule in declared order.
3. If ANY rule fails a predicate, immediately return `Decision(status=DENY, rule_id=rule["id"], reason=f"predicate_failed:{failed}", next_action=on_deny["redirect"])`.
4. Only return `ALLOW` when EVERY matching rule passes all its required predicates.

### Fix B: Graceful Target Pruning in `closeout_gate.py`
In `targeted_candidate(repo, targets, base_ref)`:
```python
if changed:
    if sorted(changed) != targets:
        pruned = sorted(set(targets) - changed)
        print(f"· Pruned unchanged targets: {pruned}")
        targets = [t for t in targets if t in changed]
    return "worktree_targeted", targets, diff
```
If some targets in `--files` do not have working-tree changes, the gate prints a notice, prunes the list to only changed targets, and continues diff extraction seamlessly. It only raises `ValueError` if there are zero changed files anywhere.

### Fix C: Runner Qualified Import (`runner.py`)
Ensure `runner.py` works seamlessly both when imported as a top-level module and as a package:
```python
try:
    from guardgate.engine import ALLOW, DENY, GuardEngine
    from guardgate.predicates import (
        check_case_161_follow_limit_ceiling,
        check_case_162_timeout_floor,
        check_dispatch_timeout_floor,
        ...
    )
except ModuleNotFoundError:
    from engine import ALLOW, DENY, GuardEngine
    from predicates import (
        check_case_161_follow_limit_ceiling,
        check_case_162_timeout_floor,
        check_dispatch_timeout_floor,
        ...
    )
```

---

## 3. Verification & Regressions
- Unit test coverage for multi-rule matching: `guardgate/test_engine.py::test_multi_rule_matching_and_first_deny` confirms that when Rule 1 passes and Rule 2 fails, Decision is `DENY` with `rule_id="r2"` and subsequent rules are not evaluated after the first denial.
- End-to-end runner test confirms that an adversarial diff modifying `follow_limit = 5` is rejected with `RULE_ID: case_161_natural_follow_limit_ceiling` and an adversarial diff modifying `connection_wait_timeout = 4.0` is rejected with `RULE_ID: case_162_usb_micro_drop_timeout_floor`.
