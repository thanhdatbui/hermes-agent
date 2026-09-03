# Mode 2′ Anchor Follow & Anti-Release Verification (2026-08-27)

## Bối cảnh & Yêu cầu
Trong flow Mode 2′ (`mode2_follow_followers.py`) của repo `D:\Taadaa\tiktok-follow`:
- Máy tìm kiếm và truy cập Profile của nick Anchor (Tik1/Tik2, `account_row_index <= 2`).
- Nếu Profile Anchor hiển thị chưa follow (`not_followed`):
  1. Kiểm tra pre-budget (`state.budget_remaining() >= 1`).
  2. Tap Follow anchor.
  3. Thực hiện vuốt kéo từ trên xuống (Pull-to-refresh) qua `pull_to_refresh_profile(sleep_after=3.5)` để reload giao diện.
  4. Dump lại UI và xác minh:
     - Nếu nút chuyển sang `followed` ("Nhắn tin" / "Đã follow"): Ghi `state.mark(uid, STATUS_FOLLOWED)`, trừ budget `state.consume_budget(1)`, ghi nhận vào `res.followed` và tiếp tục mở tab Following.
     - Nếu nút quay lại `not_followed` ("Follow"): Đánh dấu `state.set_follow_failed()`, trả `FOLLOW_FAILED`, dừng toàn bộ session ngay lập tức (không thử anchor khác, không gọi `recover_ui`, không chuyển sang Mode 1 bù lượt).

## Các Pitfalls Kỹ Thuật Đã Xử Lý (Commit `efd0705`)

### 1. Ghi nhận Anchor Follow khi Downstream Mở Tab Thất Bại
- **Vấn đề**: Nếu tap follow anchor thành công và verify reload OK, nhưng sau đó việc tap vào tab "Đã follow" (Following) bị fail cả 2 lần retry, kết quả `res.followed` nếu chỉ ghi sau khi mở tab thành công sẽ bị thiếu mất nick anchor (trong khi state và budget đã ghi nhận).
- **Giải pháp**: Ngay sau khi `_ensure_anchor_followed` trả về profile XML hợp lệ (đã follow), cập nhật `res.followed.append(uid)` và `used += 1` với per-session dedupe guard (`anchor_charged`) để không bị cộng lặp khi retry.

### 2. Bảo toàn trạng thái `FOLLOW_FAILED` ở vòng Retry Ladder
- **Vấn đề**: Khi mở tab Following lần 1 fail (do UI lag), `run_mode2` gọi `recover_ui()` rồi thử `_open_following_tab` lần 2. Nếu ở lần 2 này anchor bị nhả follow (hoặc phát sinh `follow_failed`), code cũ gán cứng `res.status = "MANUAL_REVIEW"` và che mất lỗi dừng khẩn cấp `FOLLOW_FAILED`.
- **Giải pháp**: Kiểm tra `if state.follow_failed:` sau cả lần thử 1 và lần thử 2 trước khi fallback sang `MANUAL_REVIEW`.

### 3. Không kiểm tra số lượng `@`-nodes quá khắt khe sau Reload
- **Vấn đề**: Kiểm tra sau reload yêu cầu `len(at_nodes) == 1` có thể bị fail oan nếu profile của anchor chứa bio mention hoặc tagged account (`@user_other`).
- **Giải pháp**: Dùng `profile_identity_from_xml` trích xuất `username` chính thức của profile và so khớp exact normalized handle với UID anchor (`_normalize_handle(identity.username) == _normalize_handle(uid)`).

### 4. Caller Subprocess từ `tiktok-luot nuoi acc`
- Subprocess gọi follow từ repo nuôi acc dùng lệnh:
  `python -m follow_runner.run_follow --machine N --config <path> --account-row-index R --skip-identity-verify` với `cwd=r"D:\Taadaa\tiktok-follow"`.
- Do gọi trực tiếp qua `-m follow_runner.run_follow` từ thư mục source code, mọi thay đổi trong source Python sẽ có hiệu lực ngay ở lần chạy kế tiếp mà không cần cài đặt lại package.
