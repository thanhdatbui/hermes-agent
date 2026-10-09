# Bẫy Widget Samsung Launcher "GALAXYESSENTIALS" & Nút "Tiếp tục" trong Add 2FA TikTok (07/09/2026)

## 1. Bẫy Bắt Nhầm Secret Key từ Widget Samsung Launcher ("GALAXYESSENTIALS")

### Hiện tượng & Cơ chế gây lỗi
- Trên màn hình chính của dòng máy Samsung S7 (`com.sec.android.app.launcher`) có widget hệ thống mang tên **"Galaxy Essentials"**.
- Sau khi loại bỏ khoảng trắng và ký tự phân cách: `GALAXYESSENTIALS` (dài đúng 16 ký tự).
- Ngẫu nhiên toàn bộ ký tự `G, A, L, X, Y, E, S, N, T, I` đều thuộc bảng mã Base32 RFC 4648 (`[A-Z2-7]`). Lệnh `generate_totp("GALAXYESSENTIALS", 0)` sinh mã thành công mà không văng lỗi.
- Trong `python_runner/core/ui_interact.py`, các hàm `_base32_candidates()` và `read_secret_node()` trước đây chỉ duyệt text/desc của các phần tử XML mà không kiểm tra thuộc tính `package` hay context TikTok.
- Khi máy ở ngoài màn hình chính Launcher (chưa mở app TikTok), runner quét trúng widget này, ngộ nhận đây là Secret Key của TikTok và lưu `secret=GALAXYESSENTIALS` vào file Journal DPAPI ở trạng thái `PhaseBState.CAPTURED`.

### Hệ quả dây chuyền
- Runner tưởng máy đã mở sẵn màn hình Secret Key của TikTok nên gán `_resume_key_screen = True`, bỏ qua toàn bộ các bước mở TikTok, vào Profile và Cài đặt bảo mật.
- Runner lập tức gọi `advance_to_otp()` để tìm nút "Tiếp" / "Tiếp tục" ngay trên... **màn hình chính Launcher Samsung**.
- Sau 4 chu kỳ cuộn không thấy nút, runner ném lỗi `LiveAdapterError("OTP_ADVANCE_BUTTON_NOT_REACHED")`.
- Mọi lần rerun hoặc chạy batch sau đó đều đọc Journal thấy state `CAPTURED` nên tiếp tục nhảy cóc vào tìm nút trên Launcher và fail lặp lại liên hoàn (làm nhiễm bẩn 24/24 file journal trên farm).

### Giải pháp kỹ thuật đã chuẩn hóa
1. **Lọc chặt Package:** Trong `_base32_candidates(elements)`, chỉ chấp nhận các element có thuộc tính package là `com.ss.android.ugc.trill` (hoặc resource-id bắt đầu bằng `com.ss.android.ugc.trill:`). Loại bỏ 100% các package hệ thống `com.sec.*`, `com.android.*`.
2. **Blacklist chuỗi rác:** Chặn trực tiếp: `if compact == "GALAXYESSENTIALS": continue`.
3. **Fail-closed trong `read_secret_node()`:** Nếu chuỗi XML hierarchy không chứa `"com.ss.android.ugc.trill"`, ném ngay `UIInteractError("current UI is not TikTok")`.
4. **Kiểm tra context trong `navigate_and_verify_account()`:** Chỉ thử đọc `read_secret_node(current)` khi `"com.ss.android.ugc.trill" in current`. Nếu màn hình đang ở Launcher thì bắt buộc gọi `_prepare_fresh_tiktok()` và `_open_profile_tab()`.
5. **Purge Journal rác:** Khi phát hiện nhiễm chuỗi rác, phải duyệt quét toàn bộ thư mục `journals/` và xóa các file `.dpapi` chứa `GALAXYESSENTIALS`.

---

## 2. Nút Chuyển Bước OTP Mang Nhãn "Tiếp tục" Thay Vì "Tiếp"

### Hiện tượng
- Trong `advance_to_otp()`, code cũ tìm kiếm cứng nhãn `"Tiếp"` với `prefix=False` (`_matches(element, "Tiếp", prefix=False)`).
- Trên các bản cập nhật TikTok mới trên Samsung S7, nút chuyển tiếp sang màn nhập mã OTP mang nhãn **"Tiếp tục"** (hoặc `"Next"` trên giao diện tiếng Anh).
- Việc so khớp chuỗi trần chính xác 100% với `"Tiếp"` dẫn tới `UI_TARGET_AMBIGUOUS:Tiếp:0`, adapter cuộn 4 lần rồi văng `OTP_ADVANCE_BUTTON_NOT_REACHED`.

### Giải pháp kỹ thuật đã chuẩn hóa
- Trong `advance_to_otp()`, duyệt danh sách nhãn ứng viên: `candidates = ["Tiếp tục", "Tiếp", "Next", "Continue"]` với cả `prefix=False` và `prefix=True`.
- Thêm vào `_BILINGUAL_LABELS`: `"Tiếp": "Next"`, `"Tiếp tục": "Next"`.
- Tối ưu chỉ dump UI 1 lần mỗi chu kỳ cuộn (`xml_text = self._dump_preflight()`), tránh gọi thừa uiautomator dump qua ADB.

---

## 3. Chống Worker Analysis Paralysis Khi Gặp `SWITCHER_OPEN_FAILED`

### Hiện tượng ngâm phiên
- Khi chạy live trên máy đơn lẻ, nếu gặp lỗi nghiệp vụ thiết bị như `SWITCHER_OPEN_FAILED` (TikTok không mở được switcher nick) hoặc `DEVICE_LOCK_UNAVAILABLE`:
- **Anti-Pattern:** Worker subagent không dừng báo cáo ngay mà tự ý đi bới ngược vào `automation-core`, gọi `computer_use`, quét `search_files` đĩa diện rộng dính lỗi `os error 2`, đọc cấu trúc `account_switcher.py`, kéo dài phiên 40-50 phút mà không đưa ra kết quả.
- **Quy tắc cưỡng chế:** Khi runner trả về kết quả terminal trạng thái máy (`failed` / `skipped` / `blocked`), worker BẮT BUỘC:
  1. Ghi nhận output runner và chụp screencap màn hình máy.
  2. Báo cáo ngay kết quả về Coordinator trong <= 5 tool calls.
  3. CẤM TUYỆT ĐỐI tự ý đào sâu reverse-engineer kiến trúc core khi chưa có chỉ thị từ Coordinator.
