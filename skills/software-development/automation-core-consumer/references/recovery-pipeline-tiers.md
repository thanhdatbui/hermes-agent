# OBSOLETE — Removed 2026-07-26

The multi-tier recovery pipeline (direct → home-reset → reopen-tiktok) and consumer-side fallbacks (`_fallback_tap_profile_tab`, `_reset_to_home_feed`, `_reopen_tiktok_clean`, `_clear_profile_subpage_before_navigation`, `_verify_clean_profile_root`) have been **removed** from all consumers.

**Current pattern:** dismiss popups (core) before/after, call `open_profile_root()` + `open_switcher()` (core only), core fail → MANUAL_REVIEW. No consumer fallback, no recovery tiers, no coordinate hacks.

See SKILL.md § ACCOUNT_SWITCHER Error Handling — Simplified (v2).
