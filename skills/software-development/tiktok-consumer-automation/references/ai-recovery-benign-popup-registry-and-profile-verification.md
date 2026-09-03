# AI Auto-Recovery & Benign Popup Registry Patterns (TikTok Consumer)

## 1. Kiến trúc Centralized Benign Popup Registry
- **Vấn đề cũ:** AI Auto-Recovery mỗi khi gặp popup lại sinh code append mù vào cuối file `benign_popup.py`, tạo ra hàng chục hàm mồ côi (orphan handlers) trùng lặp cho cùng một màn hình (Camera, Location, Live overlay) trên 80 máy.
- **Giải pháp chuẩn hóa (`benign_popup_registry.py`):**
  * Định nghĩa `RegistryEntry` có kiểu dữ liệu rõ ràng: `(name, priority, detector, dismisser, enabled, source, created_at)`.
  * `dismiss_allowed_generic_popup` và `dismiss_any_popup` thực hiện **Dual-Path Dispatch**: duyệt qua Registry theo thứ tự ưu tiên `priority` trước khi fallback về core cũ.
  * Các handler mặc định do kỹ sư định nghĩa (`source="manual"`) được bảo vệ an toàn, cấm AI ghi đè.

## 2. Bộ lọc Deduplication & AST Validation trong AI Patcher
- **Deduplication Check:** Trước khi sinh code patch mới, kiểm tra `is_duplicate_handler`:
  * Trùng tên hoặc có độ tương đồng keyword / text marker >= 80% với entry đã có trong Registry.
  * Nếu trùng: Bỏ qua bước sinh code patch, chỉ gửi lệnh ADB gỡ kẹt tại chỗ để máy lướt tiếp ngay.
- **AST Security Validation:**
  * Parse code qua `ast.parse()`, kiểm tra block các lệnh nguy hiểm (`os.system`, `subprocess`, `shutil.rmtree`, `eval`, `exec`).
  * Sử dụng cơ chế ghi file an toàn (Atomic write qua file temp + `os.replace` dưới `GIT_PATCH_LOCK`).

## 3. Sửa lỗi Emergency Rollback (git revert SHA cụ thể)
- **Lỗ hổng nguy hiểm:** Lệnh rollback cũ gọi `git revert HEAD` dẫn đến việc nếu máy B vừa commit một tính năng mới lên master, máy A bị lỗi rollback sẽ revert nhầm commit mới nhất của máy B.
- **Quy tắc bắt buộc:**
  * Lưu chính xác commit SHA khi patch: `counter[error_key]["sha"] = commit_sha`.
  * Khi rollback: Bắt buộc dùng `git revert --no-edit <recorded_sha>`, kiểm tra SHA hợp lệ trước khi revert, acquire Git lock mutex để không conflict giữa các máy.

## 4. Classifier Integration & Camera/Video Creation Screen
- **Nguyên nhân dừng phiên giả:** Khi người dùng quẹt nhầm vào nút `[+]` (Camera/Tạo video) trên TikTok, `classifier.py` không nhận diện được màn hình quay video nên gán nhãn `unknown` / `unexpected popup/dialog marker detected` ➔ dừng phiên và báo động Telegram.
- **Xử lý tận gốc:**
  * Bổ sung nhận diện các marker đặc trưng của Camera/Video screen (`10 phút`, `60s`, `15s`, `ảnh`, `văn bản`, `đăng`, `tạo`, `10m`, `photo`, `templates`) vào `classify_tiktok_screen`.
  * Gán nhãn `GENERIC_POPUP_SCREEN` để luồng feed tự động kích hoạt `benign_popup_registry` gửi phím `BACK` thoát camera và tiếp tục lướt feed mà không cần dừng phiên.

## 5. Quy tắc Đối soát Profile (Strict Evidence Gate)
- **Bài học từ Sol Audit:** *Không xác minh được Profile ≠ Tài khoản không khớp*.
- Khi tap vào tab "Hồ sơ" ở cuối phiên, nếu bị kẹt Camera/Overlay hoặc mạng chậm chưa load profile, màn hình sẽ không có `@username`.
- **Tuyệt đối không kết luận `profile account mismatch`** khi màn hình hoàn toàn thiếu thông tin user ID. Trạng thái này phải là `profile-identity-unavailable` / `inconclusive`, cần thoát overlay và thử recalibrate navigation thay vì vội vàng dừng phiên và báo sai tài khoản.
