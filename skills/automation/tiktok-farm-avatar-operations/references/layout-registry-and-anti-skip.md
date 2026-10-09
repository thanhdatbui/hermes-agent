# Layout Registry, Regression Gate & Anti-Skip Invariant for TikTok Farm

## 1. Multi-Layout Architecture on Profile Screen (`profile_layouts`)
TikTok updates UI continuously across account cohorts, resulting in distinct Profile layouts on the farm:
- **Layout 1 (Classic Text Layout):**
  * Identified by the prominent button with text "Sửa hồ sơ" / "Edit profile" (`ClassicTextLayout`).
  * Action: Tap the center of the text button.
- **Layout 2 (Right Pencil Layout):**
  * Seen on newer cohorts and secondary accounts where the large "Sửa hồ sơ" button is absent.
  * Identified by the small pencil icon located immediately to the right of the username/display name (`RightPencilLayout`).
  * Action: Tap the pencil icon center. Tapping this directly opens the Edit Profile screen.
- **Layout 3 (Top Left Pencil Layout):**
  * Pencil icon on the upper left header (`TopLeftPencilLayout`).
  * **Critical Exclusion:** Must strictly exclude the Back button (`[24,96][126,204]`). Tapping the Back button exits the Profile screen instead of editing.
- **Forbidden Deeplink Fallback:**
  * Never fallback to `am start -d snssdk1233://profile/edit`. This invalid intent triggers TikTok's platform warning popup *"Hoạt động này không có sẵn trên tài khoản ban đầu"*.
  * 100% of accounts can edit profile via the UI pencil or text button.

## 2. Regression Gate (`test_profile_golden.py` & `MANIFEST.lock`)
To prevent changes to one layout from breaking other account cohorts:
- **Golden XML Corpus:** Real UI dumps from different device cohorts are archived under `tests/golden/profile/<layout>/<case_id>/dump.xml`.
- **Ratchet Mechanism:** Corpus size cannot shrink (`MIN_CASES` check).
- **Tamper-Proof Lock:** `MANIFEST.lock` stores SHA256 checksums of all `expected.json` files and validates them against Git HEAD commit to prevent silent modifications during test passes.
- **Verification Command:** Always run `python -m pytest tests/test_profile_golden.py -q` before proposing selector changes.

## 3. Physical Anti-Skip Gate Enforcement
Anti-skip is not an advisory rule; it is enforced physically with non-zero exit codes across 3 gate layers:
1. **Worker Cage (`tools/cage_gate.py`):**
   * Inspects `git diff` of the worker target file. Rejects with exit 1 if any evasion patterns (`status = "SKIPPED_*"`, `action = "safe_skip"`, `edit_state == "unavailable" ... return True`) are found.
2. **Closeout Gate Step 2.5 (`tools/guard_selector_change.py`):**
   * Rule R6 blocks the closeout pipeline if any script diff introduces safe-skip or fake success logic.
3. **Coordinator Gate (`tools/done_gate.py`):**
   * Scans both working tree and staged diffs for evasion patterns and requires fresh real-device canary proof (< 2h).

## 4. Visual Evidence Invariant & Device State
- **Screen-On Preflight:** Always verify `Screen: ON (Awake)` before taking screenshots. Samsung S7 in sleep mode produces a 12KB pitch-black image that is rejected by canary verifiers.
- **Full-Screen Evidence:** Deliver full 1080x1920 screenshots (`MEDIA:<path>`). Never crop only the header or a sub-region when reporting layout differences to the operator. User strictly requires full-screen context to evaluate overall UI state.

## 5. Clean Single-Path Transition (Chống Over-Engineering & Fallback Rác)
- **Chuẩn hóa điểm vào Sửa hồ sơ:**
  * Chỉ có 2 điểm vào duy nhất đã được Regression Gate giải quyết: Nút to "Sửa hồ sơ" (`ClassicTextLayout`) và cây bút chì (`RightPencilLayout`).
  * Tap đúng điểm vào -> Đợi `_wait_for_avatar_edit_screen` -> Màn bung ra `ready` -> Chạy thẳng tiếp tục luồng up avatar chuẩn (chọn ảnh, crop, save).
- **Triệt tiêu toàn bộ fallback rác:**
  * CẤM tap vào avatar circle trên màn Profile (dễ bị ăn nhầm Story viewer hoặc camera).
  * CẤM gọi deeplink intent `snssdk1233://profile/edit` (gây văng popup lỗi).
  * CẤM viết chuỗi fallback 4-5 tầng xử lý popup `unavailable`.
  * Nếu sau 1 lần vuốt nhẹ đưa header về đỉnh mà vẫn không thấy nút/bút chì: fail-closed ngay lập tức với `WorkflowError(AVATAR_EDIT_BUTTON_NOT_FOUND)`.

## 6. Thoát Hiểm Khi Kẹt Coordinator Dispatch Budget (Claude Code CLI) & Ranh Giới "Kiểm Tra" vs "Sửa"
- **Ranh giới tối thượng khi User bảo "kiểm tra lại" / "check lại":**
  * Lệnh kiểm tra là lệnh READ-ONLY O(1). Coordinator BẮT BUỘC chỉ đọc log, inspect máy hoặc test thử dispatch rồi báo cáo đúng hiện trạng cho User.
  * CẤM TUYỆT ĐỐI tự ý kích hoạt Claude Code CLI chạy ngầm sửa file hay staging git khi User chỉ bảo "kiểm tra lại".
- **Điều kiện duy nhất được phép gọi Claude CLI:**
  * Chỉ gọi Claude CLI (`claude -p "..." --dangerously-skip-permissions --max-turns 10`, `background=True`) khi: (a) Đang trong task Fix Code mà Coordinator kẹt trần dispatch budget (10/10) hoặc kẹt quota ghi T1 VÀ mục tiêu sửa code đã được User phê duyệt rõ ràng, HOẶC (b) User trực tiếp ra lệnh "sửa đi", "làm đi".
  * Tuyệt đối không được nhầm lẫn giữa việc "kiểm tra hệ thống" với việc "tự ý tiến hành code surgery".
