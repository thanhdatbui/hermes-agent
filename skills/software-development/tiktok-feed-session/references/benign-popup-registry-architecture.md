# Kiến Trúc Centralized Benign Popup Registry & AI Auto-Recovery Safety (2026-08-21)

## 1. Vấn Đề Gốc Rễ Đã Khắc Phục (Root Cause)

1. **Bug append-only trong `code_patcher.py`**:
   - Trước đây AI Auto-Recovery tự sinh code vá và chỉ `append` vào cuối file `benign_popup.py`.
   - Các hàm này không được đăng ký vào Dispatcher chính (`dismiss_allowed_generic_popup` / `dismiss_any_popup`) nên trở thành **dead code**.
   - Khi máy khác gặp lại cùng một popup (Camera, Vị trí...), hệ thống tưởng là lỗi mới và liên tục sinh code vá trùng lặp.

2. **Lỗi chuỗi điều kiện chặn fallback trong `feed_swipe_smoke.py`**:
   - Trong `_dismiss_allowed_or_blanket_popup`, điều kiện gọi fallback sang `dismiss_any_popup` bị hardcode chuỗi `"not in the benign allowlist"` trong khi core trả về `"popup is not in the shared TikTok allowlist"`.
   - Dẫn đến script bỏ qua hoàn toàn các hàm mở rộng, lập tức dừng phiên và báo lỗi về Telegram.

3. **Lỗi Emergency Rollback `git revert HEAD`**:
   - `attempt_rollback()` cũ gọi `git revert HEAD` thay vì revert đúng SHA của commit lỗi (`git revert <recorded_sha>`).
   - Khi có nhiều máy commit đan xen, lệnh rollback đã revert nhầm commit mới nhất của máy khác.

---

## 2. Thiết Kế Chuẩn Hóa (Đã qua Audit GPT-5.6-Sol & Claude Opus 5 Max)

### A. Module Tập Trung: `benign_popup_registry.py`
- Định nghĩa `RegistryEntry(name, priority, detector, dismisser, enabled, source, created_at)`.
- `priority: 1..100` (số lớn chạy trước).
- Bảo vệ `source="manual"` không cho phép AI tự động ghi đè lên các hàm thủ công chuẩn.
- Các handler built-in sẵn:
  * `camera_creation_overlay` (priority 90): Phát hiện màn hình tạo ảnh/video/camera -> Gửi `KEYCODE_BACK` (4).
  * `location_permission_prompt` (priority 85): Phát hiện popup cấp quyền vị trí ("Xem nội dung phù hợp và địa điểm lân cận") -> Tap nút "Hủy" hoặc Back.
  * `live_campaign_overlay` (priority 80): Phát hiện sheet/popup sự kiện Live room -> Gửi `KEYCODE_BACK`.
  * `inapp_browser_overlay` (priority 75): Phát hiện màn hình trình duyệt / webview -> Gửi `KEYCODE_BACK`.

### B. Dual-Path Dispatch An Toàn Trong `benign_popup.py`
- Trong `dismiss_allowed_generic_popup` và `dismiss_any_popup`:
  * Sử dụng **Relative Import**: `from .benign_popup_registry import find_matching_handler` để đảm bảo duy nhất 1 instance Registry trên toàn bộ package.
  * Toàn bộ khối Registry lookup được bọc trong `try...except` để đảm bảo 100% không làm crash luồng fallback về core cũ.
  * Dismisser chỉ trả `dismissed=True` khi đã thực hiện thành công action qua ADB/Actions (`action_performed = True`).

### C. Lớp Bảo Mật AST & Deduplication trong `code_patcher.py`
- **Deduplication**: So khớp tên và từ khóa logic; nếu đã có trong Registry thì skip code patch, chỉ gửi lệnh ADB gỡ máy.
- **AST Security**:
  * Hàm `_resolve_call_name(node)` phân tích toàn bộ chuỗi attribute (chain).
  * Chặn gọi các hàm nhạy cảm (`system`, `popen`, `rmtree`, `__import__`, `eval`, `exec`, `subprocess`).
- **Atomic File Write**: Ghi ra file `.tmp` rồi `os.replace` dưới `GIT_PATCH_LOCK` để chống race-condition giữa 80 máy.
- **Rollback chuẩn**: Chỉ gọi `git revert --no-edit <recorded_sha>` với mutex lock.

---

## 3. Quy Trình Vận Hành Khi Gặp Popup Mới

1. **Khuyến khích khai báo Registry trước**: Nếu gặp popup mới lặp lại nhiều trên farm, chủ động thêm `RegistryEntry` vào `benign_popup_registry.py` với `source="manual"`.
2. **AI Auto-Recovery tự động**: Nếu AI xử lý, nó sẽ tự động gán vào Registry với `source="ai_generated"` và priority thấp hơn, tự động kiểm tra cú pháp AST và chạy test suite trước khi commit.
