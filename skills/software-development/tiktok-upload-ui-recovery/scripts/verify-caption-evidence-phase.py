"""Verify a RED-only caption evidence phase in tests/test_tiktok_workflow.py.

Ad-hoc verification (NOT suite-green proof): for a RED evidence round, pytest exit 1
is the CORRECT outcome. This script asserts the expected shape instead:
  - test file pure LF + AST-parses (no patch damage / class clobber),
  - pre-existing evidence tests PASS (control),
  - new RED tests FAIL with their discriminating assertion text (not typos/NameError),
  - neighbor classes still pass (no collateral damage),
  - git diff --check clean.

Usage (from repo root D:\\Taadaa\\Tiktok-video):
    python C:\\Users\\Kibe\\AppData\\Local\\Temp\\hermes-verify-caption-evidence.py
Next round: update NEW_TESTS / OLD_TESTS / NEIGHBORS to the round's test names.

Exit: 0 all checks passed, 1 any check failed.
"""
import ast
import subprocess
import sys
from pathlib import Path

REPO = Path(r"D:\Taadaa\Tiktok-video")
TEST = REPO / "tests" / "test_tiktok_workflow.py"
PYTEST = [sys.executable, "-m", "pytest", "-q"]

# --- per-round: update these ------------------------------------------------
OLD_TESTS = [  # must PASS (GREEN control)
    "test_f1_generic_edit_reusing_caption_bounds_returns_none",
    "test_f2_clear_sends_no_keys_when_posttap_focus_is_generic",
    "test_f3_clipboard_no_paste_tap_before_caption_identity",
    "test_f6_backup_only_resource_id_never_selected_as_caption_field",
]
NEW_TESTS = [  # must FAIL on the discriminating assertion (RED)
    ("test_f2_p1_1_clear_omits_keys_when_caption_focused_attr_missing",
     "assert keyevents == []"),
    ("test_f6_p1_2_backup_impostor_center_never_selected_as_caption_field",
     'assert selected["center"] != backup_center'),
    ("test_f3_p1_3_no_paste_tap_when_exact_caption_node_unfocused",
     "assert paste_coords not in taps"),
]
NEIGHBORS = [  # must PASS — catches class-declaration clobber from bad patches
    "tests/test_tiktok_workflow.py::TestPostHandler::test_final_composer_taps_stable_post_resource",
    "tests/test_tiktok_workflow.py::TestCaptionFill::test_clear_caption_input_uses_single_long_delete",
    "tests/test_tiktok_workflow.py::TestCaptionFill::test_clear_caption_input_reidentifies_same_field_bounds",
]
# ----------------------------------------------------------------------------

failures = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


raw = TEST.read_bytes()
check("pure LF (0 CRLF)", b"\r\n" not in raw, f"CRLF={raw.count(b'\r\n')}")
try:
    ast.parse(raw.decode("utf-8"))
    check("AST parse", True)
except SyntaxError as exc:
    check("AST parse", False, str(exc))

# Class run: old GREEN + new RED, failures reach the discriminating assertion.
res = subprocess.run(
    PYTEST + ["tests/test_tiktok_workflow.py::TestCaptionEvidencePhase"],
    cwd=REPO, capture_output=True, text=True, timeout=300,
)
out = res.stdout + res.stderr
for name in OLD_TESTS:
    check(f"old GREEN: {name}", f"FAILED tests/test_tiktok_workflow.py::{name}" not in out)
for name, needle in NEW_TESTS:
    check(f"new RED: {name}", f"FAILED tests/test_tiktok_workflow.py::{name}" in out)
    check(f"  discriminating assertion: {needle}", needle in out)

res2 = subprocess.run(PYTEST + NEIGHBORS, cwd=REPO, capture_output=True,
                      text=True, timeout=300)
out2 = res2.stdout + res2.stderr
check(f"neighbors pass ({len(NEIGHBORS)})", f"{len(NEIGHBORS)} passed" in out2,
      f"rc={res2.returncode}")

res3 = subprocess.run(["git", "diff", "--check"], cwd=REPO, capture_output=True,
                      text=True, timeout=60)
check("git diff --check clean", res3.returncode == 0)

print("\n" + ("ALL CHECKS PASSED" if not failures else f"FAILED CHECKS: {failures}"))
sys.exit(1 if failures else 0)
