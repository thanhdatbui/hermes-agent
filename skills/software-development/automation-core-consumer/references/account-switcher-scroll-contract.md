# Account Switcher Missing Account & Swipe-to-Reveal Contract

## Background
On devices with high account density (e.g. device 51 hosting 8+ accounts, or screens with low vertical height/large display scaling), TikTok's bottom-sheet account switcher dialog does not display all registered accounts in the initial viewport. Only the top 3-4 accounts are rendered into the accessible UI XML hierarchy.

## Root Cause
When calling `select_exact_account(adapter, target_account)`:
- If `target_account` is located further down the switcher list, `find_exact_account(_dump(adapter), account)` fails immediately on the initial viewport.
- An `AccountSwitcherError("ACCOUNT_MISSING", ...)` is raised without attempting to scroll the list down.

## Contract & Fix Pattern

### 1. Adapter Swipe Capability
Consumers interfacing with `automation_core.tiktok.account_switcher` via duck-typed adapters (`TikTokAdapter` in `Tiktok-video/scripts/tiktok_workflow/adapter.py`) must implement `swipe`:

```python
def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> None:
    """Swipe across coordinates via ADB shell input swipe."""
    if self.dry_run:
        logger.info(f"[DRY-RUN] swipe({start_x}, {start_y}, {end_x}, {end_y}, {duration_ms}ms)")
        return

    result = self._adb.shell(
        ["input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)],
        timeout=15,
        check=False,
    )
    if not result.ok:
        raise AccountSwitcherError(
            "SWIPE_FAILED",
            f"swipe ({start_x}, {start_y}) -> ({end_x}, {end_y}) failed",
        )
```

### 2. Core `select_exact_account` Scroll Loop
In `automation_core.tiktok.account_switcher.py`, `select_exact_account` must support scrolling with bounded retry (e.g. max 3 swipes):

```python
def select_exact_account(
    adapter: Any,
    account: str,
    *,
    settle: float = 0.05,
    max_scrolls: int = 3,
) -> str:
    xml_text = _dump(adapter)
    node = None
    last_err = None

    for attempt in range(max_scrolls + 1):
        try:
            node = find_exact_account(xml_text, account)
            break
        except AccountSwitcherError as exc:
            if exc.code == "ACCOUNT_MISSING" and attempt < max_scrolls and hasattr(adapter, "swipe"):
                last_err = exc
                # Default vertical swipe upwards within switcher dialog bounds
                # e.g., center X (540), swipe from 70% height to 40% height
                adapter.swipe(540, 1500, 540, 900, 350)
                time.sleep(max(0.1, settle))
                xml_text = _dump(adapter)
                continue
            raise

    # Proceed with selection or dismissal
    ...
```

### 3. Testing Pitfalls
- When testing `Tiktok-video` repo with `pytest`, invoking global `pytest` from the workspace root or without file paths can collide with multiple `test_tiktok_workflow.py` files in backup/run directories (`runs/...`).
- Always pass an explicit file path: `pytest tests/test_tiktok_workflow.py` or run isolated unit tests in `automation-core/tests/test_account_switcher_preconfirmed.py`.
