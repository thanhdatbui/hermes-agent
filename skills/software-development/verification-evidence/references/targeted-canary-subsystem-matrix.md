# Targeted Canary Subsystem Matrix & Gate Guard Architecture

## 1. Problem Statement: "Canary Máy Móc" (Generic Canned Canary Trap)
Agents frequently fall into the trap of running a generic canned test (e.g., swiping 3 videos on TikTok feed or checking that `exit_code == 0` without a Home screen) to claim "Canary Passed", regardless of what was actually modified in `git diff`.
- A fix in `account_switcher` proved by a video feed swipe is **UNVERIFIED**.
- A fix in `2fa_login` proved by opening Profile without auth verification is **UNVERIFIED**.
- A fix in `avatar_upload` proved without profile pHash / crop verification is **UNVERIFIED**.

## 2. Tri-Party Architectural Alignment (18/10/2026)
Following the Tri-Party Consultation Protocol (Sol High Auditor + Claude Planner + Hermes Coordinator):
- **Sol High Auditor (:20129):** CONDITIONAL APPROVE. Requires strict fail-closed enforcement:
  1. *No silent bypass:* Unmapped diffs without explicit fallback MUST fail-closed (`BLOCK`), never fall through to generic feed swipe.
  2. *Mechanical OCR Whitelist:* Must combine required keyword groups (`required_all`) + anti-launcher dominance (`LAUNCHER_DOMINANT` when >= 2 markers or 0 required groups met) + minimum characters (`min_chars >= 20`).
  3. *O(1) Hook hard deadline:* Timeout = FAIL. Cache bound to `diff_sha256`. No infinite retry converting failures to passes.
- **Claude Planner:** Designed the 4-stage interface pipeline:
  `git diff ──▶ canary_plan.py ──▶ canary_runner.py ──▶ validate_evidence_screen.py ──▶ done_gate.py`
- **Hermes Coordinator:** Implemented Phase 1 (P0: declarative matrix, read-only plan builder, OCR spec validator) and enforces operational discipline: run mechanically without stopping to ask permission or complain ("chạy bình thường, không khóc lóc").

## 3. Declarative Matrix Specification (`tools/canary_matrix.json`)
The matrix decouples mapping rules from runtime code:
```jsonc
{
  "schema_version": 1,
  "repos": {
    "tiktok-luot nuoi acc": {
      "mode": "shadow", // off | shadow | enforce
      "exempt_globs": ["**/*.md", "**/tests/**", "tests/**", "docs/**", "**/*.example.yaml"],
      "rules": [
        {
          "id": "account-switcher",
          "path_globs": ["*switcher*", "*profile_switch*", "**/flows/profile*", "*account_switcher*"],
          "hook": "account_switcher",
          "scope": "single",
          "ocr": {
            "required_all": [["chuyển tài khoản", "thêm tài khoản", "switch account", "add account"]],
            "forbidden_extra": ["launcher", "màn hình chính"],
            "min_chars": 20
          }
        },
        {
          "id": "feed-swipe",
          "path_globs": ["**/flows/swipe*", "**/flows/feed*", "*feed_swipe*"],
          "hook": "feed_swipe",
          "scope": "single",
          "ocr": {
            "required_all": [["dành cho bạn", "đang follow", "bạn bè"]],
            "min_chars": 20
          }
        }
      ],
      "fallback": {"hook": "full_flow", "scope": "single", "coverage": "generic"}
    },
    "tiktok-follow": {
      "mode": "shadow",
      "exempt_globs": ["**/*.md", "docs/**", "tests/**", "**/*.example.yaml"],
      "rules": [
        {
          "id": "follow-tab-nav",
          "path_globs": ["follow_runner/ui/*tab*.py", "follow_runner/flows/following*.py"],
          "hook": "open_following_tab",
          "scope": "single",
          "ocr": {
            "required_all": [["following", "đang follow", "đã follow"]],
            "min_chars": 20
          }
        },
        {
          "id": "follow-core",
          "path_globs": ["follow_runner/run_follow.py", "follow_runner/core/**"],
          "hook": "full_flow",
          "scope": "wide",
          "ocr": {
            "required_all": [["follow"]],
            "min_chars": 20
          }
        }
      ],
      "fallback": {"hook": "full_flow", "scope": "single", "coverage": "generic"}
    }
  }
}
```

## 4. Interface Contracts

### 4.1 `canary_plan.py` (Read-Only Diff Analysis)
- Invokes `git diff --no-ext-diff -U0 --no-color <base> HEAD`.
- Computes canonical `diff_sha256` by normalizing EOL and whitespace.
- Filters `exempt_globs` (docs, tests, examples).
- Matches changed paths to rule `path_globs`. If unmapped, assigns repo fallback or fails.
- Generates `canary_plan.json` containing:
  - `diff_sha256`, `base_sha`, `head_sha`, `matrix_sha256`.
  - `requirements`: list of required rules, hooks, scopes, and OCR specs.
  - `unmapped` and `exempt` path audits.

### 4.2 `validate_evidence_screen.py` (`validate_ocr_spec`)
- `validate_ocr_spec(image_path, spec, ocr_fn) -> (bool, status, details)`:
  1. Checks `image_path` existence and minimum file size (`OCR_MIN_FILE_BYTES = 40000`).
  2. Runs WinRT OCR (or injected `ocr_fn` for mock tests).
  3. Checks `len(ocr_text.strip()) >= spec.get('min_chars', 20)`.
  4. Evaluates `required_all`: Each element is a list of synonymous keywords; at least one keyword in each group must hit.
  5. Evaluates Launcher Dominance: If $\ge 2$ launcher markers appear, or $\ge 1$ launcher marker appears while 0 required groups are satisfied $\rightarrow$ Returns `(False, "LAUNCHER_DOMINANT", details)`.
  6. Returns `(True, "VALID", details)` with `ocr_text_sha256` and matched `hits`.
- CLI flag `--spec-json` allows standalone execution or integration by `canary_runner` and `done_gate`.

### 4.3 `canary_runner.py` (Receipt v2 Execution)
- Supports `--plan <plan.json>` CLI argument: automatically resolves `repo`, `target_machines`, and `diff_sha256`.
- Emits **Receipt v2** (`schema: 2`): includes `diff_sha256`, `plan_sha256`, and per-requirement evidence while maintaining backward compatibility with Receipt v1 fields (`media_path`, `media_sha256`, `commit_sha`).

### 4.4 `done_gate.py` (Delegated Check & Single Source of Truth)
- `done_gate.py` is refactored from a standalone ad-hoc script into a lightweight delegation wrapper around `canary_runner.check_canary_status()`.
- Single Source of Truth: All canary status verification (TTL 2h, Receipt v2 schema, `diff_sha256` binding, `plan_sha256`, media file existence >= 40KB, media SHA256 integrity, single/wide scope matching) is implemented once in `canary_runner.py` and invoked via `canary_runner.py --check` or imported by `done_gate.py`.
- Recognizes Receipt v2 and inspects `plan_sha256` / `diff_sha256` binding against repo working tree.
- Operates in `shadow` mode before upgrading to `enforce`. In `enforce` mode, mismatch between git diff and receipt diff immediately fails closed.

## 5. Phased Rollout Discipline
1. **Phase 0 (P0 - Completed):** `canary_matrix.json`, `canary_plan.py`, and `validate_ocr_spec()` unit-tested (12/12 pytest pass).
2. **Phase 1 (P1 - Completed):** Runner integration with `--plan <plan.json>`, Receipt v2 generation, `done_gate.py` shadow alignment, and full test suite verification (16/16 pytest pass in 0.24s).
3. **Phase 2 (P2 - Next):** Switch repo `mode` from `shadow` to `enforce` once seed keywords and hooks are fully verified on real hardware.

## 6. Anti-Halting Discipline ("Làm đi đừng có dừng lại hỏi")
- **Core Operator Invariant:** When the operator directs execution ("R triển khai đi", "Làm luôn đi", "Fix đi"), the agent must execute continuously through to completion without pausing at every intermediate step to ask rhetorical permission ("Sếp có đồng ý không?", "Em bắt đầu làm nhé?").
- **No Complaining / No Whining:** If a worker reaches maximum turns or a command fails, do not throw hands up, do not produce psychological self-blame essays, and do not freeze. Immediately inspect the diff, salvage working code, write focused unit tests, patch defects, and verify until the job is DONE with concrete proof.
