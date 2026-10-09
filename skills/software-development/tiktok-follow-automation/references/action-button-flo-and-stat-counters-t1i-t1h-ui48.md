# Case UI-48: Action Button id/flo & Stat Counters id/t1i, id/t1h (Machine 50 Triage)

## Triệu chứng & Bối cảnh
- **Farm Alert**: `[MÁY 50] DỪNG PHIÊN`
- **Quy trình / Script**: Follow TikTok (`tiktok-follow`)
- **Máy**: 50 | **Serial**: `ce091609dd78991305` | **Nick**: `hng.th.v713`
- **Lỗi dừng**: `MANUAL_REVIEW: không thấy đúng một nút Follow trên exact profile`

## Root Cause
- TikTok trên Máy 50 cập nhật layout Profile mới:
  1. Cụm nút hành vi (Action buttons) đổi sang `resource-id="com.ss.android.ugc.trill:id/flo"`:
     - Nút Follow: `text="Follow"`, `resource-id="com.ss.android.ugc.trill:id/flo"`, `bounds=[114,789][462,921]`
     - Nút Nhắn tin: `text="Nhắn tin"`, `resource-id="com.ss.android.ugc.trill:id/flo"`, `bounds=[474,789][822,921]`
  2. Cụm chỉ số thống kê (Stat counters) đổi sang:
     - `id/t1i`: Node số đếm (`text="0"`, `text="5"`, `text="0"`)
     - `id/t1h`: Node nhãn thống kê (`text="Đã follow"`, `text="Follower"`, `text="Thích"`)
- Trong `follow_runner/flows/verify_follow.py`:
  - `_ACTION_BUTTON_SUFFIXES` chỉ chứa: `(":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/follow_button")`, thiếu `id/flo`.
  - `_STAT_COUNTER_IDS` chỉ chứa: `("id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut", "id/svu")`, thiếu `id/t1i`, `id/t1h`.
- Hệ quả:
  - `_is_profile_action_node` trả về `False` với nút Follow trên màn hình $\rightarrow$ `classify_button` không tìm thấy node action $\rightarrow$ trả về `unknown` $\rightarrow$ `_classify_exact_profile_action` ném `MANUAL_REVIEW: không thấy đúng một nút Follow trên exact profile`.

## Giải pháp (Fix Codebase)
1. **`follow_runner/flows/verify_follow.py`**:
   - Thêm `":id/flo"`, `"id/flo"` vào `_ACTION_BUTTON_SUFFIXES` (và alias `_ACTION_BUTTON_IDS`).
   - Thêm `"id/t1i"`, `"id/t1h"` vào `_STAT_COUNTER_IDS` để đảm bảo các node số đếm và nhãn thống kê không bao giờ bị nhận nhầm thành nút hành vi.
2. **`scripts/run-follow.ps1`**:
   - Cập nhật default parameters sang `Machine = 50` và `Config = "config/machine50.yaml"` để phục vụ canary nhanh.

## Regression Tests
- File: `follow_runner/tests/test_verify_follow.py`
  - `test_classify_machine50_action_button_id_flo_and_stat_t1i_t1h`: Kiểm tra `not_followed` và `followed` trên các biến thể nút `id/flo` (cả gói `com.ss.android.ugc.trill` và `com.zhiliaoapp.musically`).
  - `test_classify_rejects_stat_counter_t1i_and_t1h_as_action_button`: Đảm bảo `id/t1i` và `id/t1h` bị loại trừ triệt để khỏi action button.
  - `test_classify_m50_current_fixture_not_followed`: Kiểm chứng trực tiếp trên file dump hiện trường `m50_current.xml`.

## Canary Verification
- Lệnh: `powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1`
- Kết quả: `FOLLOW_RESULT {"machine": 50, "status": "OK", "failed": false, "follow_failed": false, "details": {"mode2_zero_following_fix": "zero-following-skip-v2"}}` (Exit code 0).
