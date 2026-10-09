# Benign Popup: Profile Milestone Dismissal & Account Switcher Triage

## 1. Profile-Surface Milestone & Celebration Popups

### Symptom
When navigating to the profile screen (`open_profile_root` / `TAP_PROFILE`) to switch accounts, the switcher header candidate search fails with `Header candidates=0` or `SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed`.

### Root Cause
TikTok displays an unhandled engagement/milestone popup over the profile screen (e.g. video like celebration or post prompt) that intercepts touch events or obscures the profile header username:
- **Milestone Like Popup**:
  - Text markers: `Tổng số lượt thích`, `đã nhận tổng cộng`, `lượt thích cho tất cả video`, or English equivalents `Total likes`, `received a total of`.
  - Close / Acknowledge element: `[OK]` button (`text="OK"` or `resource-id=".../button"`).
- **Post Prompt / Composer Overlay**:
  - Text markers: `Bạn đang nghĩ gì...`, `What's on your mind...`.

### Integration into Automation Core (`benign_popup.py`)
Add benign popup classification rule under `automation_core.tiktok.benign_popup`:
- Rule name: `PROFILE_MILESTONE_LIKES`
- Detection criteria:
  - Any marker from `["tổng số lượt thích", "đã nhận tổng cộng", "total likes"]`
  - Close element matching `text="OK"` or `content_desc="OK"`
- Surface timing:
  - Must be invoked inside `DISMISS_POPUPS` and pre-checked immediately before `prepare_switcher_anchor` / `open_switcher`.

---

## 2. False-Positive Session Loss Triage (`ACCOUNT_SWITCHER_FAILED`)

### Distinction: Session Eviction vs. Missing Target Slot
A batch failure reporting `ACCOUNT_SWITCHER_FAILED` with `ACCOUNT_MISSING` is frequently misclassified by alert monitors as `MẤT PHIÊN / VĂNG ACCOUNT`:

| Case | UI Evidence (Switcher Panel) | Root Cause | Proper Action |
|---|---|---|---|
| **True Session Loss** | TikTok redirects to Guest Feed, Log in screen, or shows `Phiên đã hết hạn` | Cookie expired, account banned, or forced password reset | Run account recovery / passwordless reset flow |
| **Missing Target Slot** | Switcher panel opens; shows only primary account (Tik 1) + `+ Thêm tài khoản`. Target account (e.g. Tik 3) is absent. | Nick was never logged into device (slot not provisioned) | Run `tiktok_login_v1.py <machine> --email <user> --ss` |
| **Obscured Switcher Header** | Profile screen loaded, but milestone dialog or banner blocks username | Popup not dismissed | Dismiss dialog via `[OK]`, re-run `open_switcher` |

### Diagnostic Procedure
1. Run WinRT OCR on `soft-reboot-account_switcher-before.png` in `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
2. If text contains `Chuyển đổi tài khoản` followed by only 1 account name, the current session is healthy; the target slot is simply unprovisioned.
3. Check `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping`) and `taikhoan_dat_v2_updated .xlsx` to verify credentials before triggering login.
