# Background Browser Automation, File Downloads & Windows "Save As" Dialog Handling

## Context & Problem
When automating web workflows on the user's primary logged-in browser (e.g. Google Chrome on Windows):
1. The user's active Chrome instance may not be started with `--remote-debugging-port=9222`.
2. Killing Chrome to attach CDP (`Stop-Process -Name chrome`) drops all active user tabs and disrupts ongoing work.
3. The user expects the agent to execute the task directly on their live session rather than giving passive advice or asking them to do it manually.

## Core Solution: Non-Disruptive Background Control via `computer_use`

`computer_use` drives the Windows desktop via `cua-driver` in `delivery_mode='background'` without stealing cursor or keyboard focus.

### 1. Identifying the Target Chrome Window
Use `computer_use(action='list_windows')` to locate the exact window:
- `app_name: 'chrome.exe'`
- Match by page title (e.g., `Lịch sử đơn hàng | Box Tài Khoản ...`)
- Note the `pid` and `window_id`.

### 2. Reliable Background Interactions on `Chrome_WidgetWin_1`
- **Synthetic Click Reliability:** In Chromium windows, synthetic mouse clicks on interactive elements (`Button`, `Hyperlink`, `ComboBox`, `CheckBox`) work reliably in background mode.
- **Form Select / Dropdown Trap:**
  - Setting `AXValue` on a Chromium `<select>` element (ComboBox) via `set_value` changes the internal accessibility text but does NOT fire the DOM `change` event (e.g., `onchange="this.form.submit()"` does not trigger).
  - *Fix:* Perform two background clicks:
    1. Click the `ComboBox` element to open the options popup.
    2. Click the target `ListItem` element (e.g., `500` or `1000`).
- **Modal Confirmation Dialogs (SweetAlert / Alertify):**
  - Web confirmation popups (e.g. "Bạn có chắc không? Hệ thống sẽ tải về đơn hàng khi bạn nhấn đồng ý") render as UIA `Window` or `Group` elements.
  - Call `capture` to get fresh SOM overlay indices, then click the confirm button (e.g., `Button 'Đồng ý'`).

### 3. Handling Native Windows "Save As" Dialogs (`#32770`)
When a web action triggers a file download that opens a native Windows file picker dialog:
1. Chrome hands off the prompt to Windows Shell, creating a window:
   - `app_name: 'chrome.exe'`
   - `title: 'Save As'`
   - Window class: `#32770`
2. Run `computer_use(action='list_windows')` to discover the newly spawned `Save As` dialog's `pid` and `window_id`.
3. Capture the dialog:
   ```json
   {
     "action": "capture",
     "mode": "som",
     "pid": <save_as_pid>,
     "window_id": <save_as_window_id>
   }
   ```
4. Find the `Button 'Save'` element (typically index ~323, bounds near bottom-right) and perform a background click:
   ```json
   {
     "action": "click",
     "delivery_mode": "background",
     "element": <save_button_index>,
     "pid": <save_as_pid>,
     "window_id": <save_as_window_id>
   }
   ```
5. The file is saved directly to `C:\Users\<user>\Downloads\<filename>` without stealing focus or raising the dialog to the front.

### 4. Expanding Vertical Viewport via Window Maximization
- Web pages with large tables may place action buttons below the visible viewport (< 900px height).
- Background mouse scroll on `Chrome_WidgetWin_1` can return `background_unavailable`.
- *Fix:* Click the window's `Button 'Phóng to'` (Maximize) button at the top right to expand the window to full 1080p, bringing more rows into view without scrolling.

## Marketplace Specifics: BoxTaiKhoan / ShopClone7
- **Order Retention Window:** BoxTaiKhoan retains order data on the server for only 3 days to ~3 weeks. Orders older than 1 month are purged per the system retention policy.
- **Order Code Format:** 17 characters (`[A-Z]{4}[0-9a-f]{13}`), e.g., `ZKJM6ab56d6a62e72`, `9MRT6ab56d5fd7e3d`, `RHEQ6ab56d5504fd4`.
- **Search Mechanics:** The `trans_id` filter field in `product-orders.php` performs an exact match against `trans_id` only (not email addresses or hardware serials).
- **Downloaded Data Structure:** Downloaded order text files contain 5 pipe-separated fields:
  `email|password|refresh_token|client_id|recovery_email`
- **Recovery Email Domain:** Hotmail accounts sold on BoxTaiKhoan use recovery mail with domain `@fviainboxes.com` (either `{username}@fviainboxes.com` or `{username}{3_random_chars}@fviainboxes.com`).
