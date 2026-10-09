# Profile Username Mismatch After Switch & Latest Run Resolution (Farm Anti-Overengineering)

## 1. Cạm bẫy đường dẫn `.ai-runs/latest/summary.txt` (Missing Latest Symlink)
- **Hiện tượng:** Prompt hoặc alert thường chỉ định:
  `Log D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt`
  Tuy nhiên trong repo `tiktok-luot nuoi acc`, thư mục/symlink `.ai-runs/latest` **không tồn tại** (trả về `FileNotFoundError`).
- **Cách tra cứu O(1) chuẩn xác:**
  Không quét đĩa đệ quy hay hoang mang. Lấy thư mục run mới nhất bằng lệnh shell 1 dòng:
  ```bash
  LATEST_DIR=$(ls -td "D:/Taadaa/tiktok-luot nuoi acc/.ai-runs"/2026* | head -n 1)
  echo "$LATEST_DIR/summary.txt"
  ```
  Hoặc nếu tìm run chứa máy cụ thể (ví dụ Máy 79):
  ```bash
  grep -rn "machine_79" "D:/Taadaa/tiktok-luot nuoi acc/.ai-runs"/2026*/summary.txt | tail -n 1
  ```

## 2. Bẫy Timeout 900s khi grep trong `python_runner`
- **Hiện tượng:** Chạy `grep -rn "<symbol>" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"` bị timeout 900s (15 phút).
- **Nguyên nhân:** Thư mục `python_runner/runs/` chứa hàng vạn file logs, JSON artifacts và screencaps của các ca chạy trước đó.
- **Quy tắc bắt buộc:**
  - **CẤM:** Không bao giờ grep trực tiếp vào `python_runner/` mà không loại trừ `runs/`.
  - **BẮT BUỘC:** Chỉ định rõ thư mục con code (`python_runner/flows/`, `python_runner/core/`) HOẶC thêm cờ `--exclude-dir=runs`:
    ```bash
    grep -n "<symbol>" "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/*.py"
    # hoặc
    grep -rn --exclude-dir=runs "<symbol>" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"
    ```

## 3. Root Cause & Giải pháp: "profile username still mismatched after switch"

### Giải pháp nhanh nhất — Nâng `PROFILE_SWITCH_MAX_ATTEMPTS` (đã fix 09/09/2026, Case 146)
- **Vị trí:** `feed_swipe_smoke.py` dòng 625: `PROFILE_SWITCH_MAX_ATTEMPTS = 2` → `= 3`
- **Khi nào áp dụng:** Nick mới (Slot 7/8, lần đầu tiên chạy feed) — TikTok app giữ nguyên profile nick cũ sau lần tap đầu, cần 1-2 lần tap bổ sung để settle. 2 lần retry không đủ; 3 lần fix được 15/80 máy.
- **Canary verify:** Sau fix, chạy `run-feed-session.ps1 -Row 7 -Machines <M> -SkipAccountWorkbookSync -MaxWorkers 1 -RecoveryTestSwipes 2 -Run`. Kết quả xanh = `profile username matched expected account`.
- **Commit:** `7430415` @ `tiktok-luot-nuoi-acc`

### Các nguyên nhân sâu hơn (nếu tăng ATTEMPTS vẫn không đủ)
- **Vị trí code:** `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` (`verify_and_switch_profile`).
- **Nguyên nhân 1 - Trễ đồng bộ UI (Settle Delay Too Short):**
  Sau khi tap chọn tài khoản trong Account Switcher (Bottom Sheet), TikTok cần thời gian tải lại phiên và cập nhật UI Profile. Nếu settle delay quá ngắn (< 3.0s), `_read_profile_identity_with_add_phone_guard` sẽ recapture màn hình khi handle cũ vẫn còn hiển thị, dẫn đến `AccountSwitcherError`.
  -> **Khắc phục:** Tăng sleep settle lên `random.uniform(3.5, 5.0)` sau khi tap switch account.
- **Nguyên nhân 2 - Tài khoản đích đã được chọn sẵn (`is_already_selected`):**
  Nếu nick đích đã có thuộc tính `selected="true"` hoặc `checked="true"` trong XML, việc tap lại có thể vô hiệu hóa hoặc không kích hoạt sự kiện switch.
  -> **Khắc phục:** Bấm phím BACK (`keyevent 4`) để đóng modal thay vì tap lại.
- **Nguyên nhân 3 - Thiếu kích hoạt Auto-Login Reconcile:**
  Khi switch thất bại dẫn đến `last_reason = "profile username still mismatched after switch"`, hàm `_is_account_switcher_missing_expected_reason(reason)` phải nhận diện được chuỗi này để cho phép gọi `_maybe_recover_missing_account_via_login(ctx, expected)`.
  ```python
  def _is_account_switcher_missing_expected_reason(reason: str | None) -> bool:
      r = str(reason or "").lower()
      return "account-switcher-missing-expected" in r or "profile username still mismatched after switch" in r
  ```
