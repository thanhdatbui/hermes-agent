# Benign Popup Test Fixtures and Keyboard Module Imports

## 1. Test Fixtures vs Production Flow Separation
- **`ADD_PHONE_XML`**: Mock XML string fixture representing the add-phone prompt UI hierarchy.
  - **Location**: `tests.test_benign_popup` (or consumer-specific test fixture module).
  - **Rule**: Never import `ADD_PHONE_XML` from `flows.benign_popup`. Production code in `flows/benign_popup.py` only implements dismiss logic (`dismiss_add_phone_popup`, etc.) and does not export test fixtures.
  - **Correct Import**:
    ```python
    from tests.test_benign_popup import ADD_PHONE_XML, make_ctx, write_verified_after_xml
    from flows.benign_popup import dismiss_add_phone_popup
    ```

## 2. Keyboard State Module Path
- **`KeyboardState`**: Dataclass representing detected IME keyboard visibility and source.
  - **Location**: `core.keyboard` (used across `flows/benign_popup.py` and device classifiers).
  - **Trap**: Do not import `KeyboardState` from `flows.keyboard_cleanup` (phantom module). This results in:
    ```
    ModuleNotFoundError: No module named 'flows.keyboard_cleanup'
    ```
  - **Correct Import**:
    ```python
    from core.keyboard import KeyboardState
    ```
