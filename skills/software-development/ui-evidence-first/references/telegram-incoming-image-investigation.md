# Telegram Incoming Image & Farm Alert Investigation Pattern

## 1. Context & Trigger
When a user sends a message on Telegram like "Fix lỗi đi", "Fix lỗi này cho t", or "Lỗi gì đây" with an image attachment but without specifying the machine number or repository in text:
- The image is saved to: `C:\Users\Kibe\AppData\Local\hermes\cache\images\img_<hash>.jpg`.
- The most recent image can be retrieved by sorting files in that directory by modification time (`os.path.getmtime`).

## 2. Direct Model Vision Inspection Protocol
Per operational policy, do NOT use `browser_vision` or auxiliary vision tools. Instead, inspect the image directly via the active LLM on the local proxy endpoint:
- **Endpoint:** `http://127.0.0.1:20129/v1/chat/completions` (or `:20128`)
- **Model:** `antigravity/gemini-3.7-flash-high` or `auto/best-vision`
- **Auth:** Bearer token from `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (`SELECT key FROM apiKeys;`)
- **Payload:** Base64-encoded JPEG in standard OpenAI-compatible image message format.

## 3. Investigation Workflow
1. **Extract Device Identifier & UI Context:**
   - Locate machine header tag (e.g., `[MAY 29]`, `[MAY 62]`).
   - Identify the active application and screen (e.g., TikTok search, following list, login dialog, Android home).
   - Detect presence of any modal popups, error dialogs, or in-app toasts.

2. **Resolve Device Serial:**
   - Look up serial from `D:\OneDrive\Tiktok\Tik1.xlsx` (column 1 = machine number, column 2 = serial) or `D:\CodexRuntime\tiktok-video\config-machine-N.yaml`.
   - Never guess serials.

3. **Cross-Check Real State vs Visual Scene:**
   - **Run State:** Check `runs/state/follow_state_<machine>_row_<ca>.json` (budget used, `follow_failed` status).
   - **Device Locks:** Check `C:\Users\Kibe\.codex\device-locks/` for blocked or active locks.
   - **Cron Watchdog:** Check latest summary under `C:\Users\Kibe\AppData\Local\hermes\cron\output/`.
   - **Live Screen Verification:** Capture fresh screencap via `"C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> exec-out screencap -p`.

4. **Distinguish Benign Screens from Actual Errors:**
   - **Benign:** In-app notification toasts (e.g., "X đã bắt đầu follow bạn"), standard following list with action buttons, completed session idle screen with `follow_failed: false`.
   - **Actionable Error:** Session logout ("Tài khoản của bạn đã bị đăng xuất"), identity mismatch, crash dialog, blocked lock held after process death.

5. **Reporting:**
   - Report strictly in the concise format: `Mục đích` -> `Kết quả` -> `Bằng chứng` -> `Blocker`.
