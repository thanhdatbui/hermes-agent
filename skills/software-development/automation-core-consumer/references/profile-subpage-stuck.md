# OBSOLETE — Removed 2026-07-26

The consumer-side subpage clearing helpers (`_clear_profile_subpage_before_navigation`, `_verify_clean_profile_root`) and the multi-tier recovery pipeline have been **removed** from all consumers.

Core handles subpage clearing internally in `open_profile_root(attempts=3)` and `leave_profile_subpage(max_back=3)`. Consumers must NOT import `leave_profile_subpage` or `is_profile_subpage` — only `open_profile_root` and `open_switcher`.

**Current pattern:** dismiss popups (core) before/after each core call, core fail → MANUAL_REVIEW. No consumer fallback.

See SKILL.md § ACCOUNT_SWITCHER Error Handling — Simplified (v2).
