# Settings & Privacy Login False-Positive & Profile Display Name Verification Pitfall (14/09/2026)

## 1. Sự cố Triage Farm Alert Batch Nuôi Acc (14/09/2026)

- **Hiện tượng:** Batch nuôi acc / lướt feed Ca 2 Row 4 (`row-4-120025`) báo alert diện rộng (22/80 máy thất bại, 27.5%), trong đó có 7 máy cảnh báo P0 văng account / mất phiên:
  - 4 máy (M1, M22, M39, M72): `profile verification mismatch: profile account mismatch`.
  - 3 máy (M24, M28, M42): `login/account screen detected`.
- **Thực tế hiện trường (Ground Truth O(1)):**
  100% CẢ 7 MÁY ĐỀU LÀ FALSE-POSITIVE, TÀI KHOẢN HOÀN TOÀN CÒN NGUYÊN PHIÊN ĐĂNG NHẬP.

---

## 2. Dạng 1: Nhầm Lẫn Màn Hình Settings & Privacy thành "Login/Account Screen" (M24, M28, M42)

- **Cơ chế lỗi:**
  - Thiết bị trong lúc lướt feed hoặc xử lý popup gặp thao tác back/drift lọt vào trang **"Cài đặt và quyền riêng tư"** (`Settings and privacy`).
  - Ở phần chân trang của menu này, TikTok luôn hiển thị 3 mục tài khoản:
    + `android.widget.TextView: Đăng nhập`
    + `android.view.View: Chuyển đổi tài khoản`
    + `android.view.View: Đăng xuất`
  - Classifier quét thấy chữ *"Đăng nhập"* $\rightarrow$ kích hoạt rule phát hiện màn hình login (`manual-needed:login`) $\rightarrow$ dừng session và báo cáo văng tài khoản sai sự thật.
- **Dấu hiệu nhận diện O(1) để phân biệt:**
  - Nếu XML chứa:
    `TextView: "Cài đặt và quyền riêng tư"` HOẶC `View: "Chuyển đổi tài khoản"` / `View: "Đăng xuất"`
    $\rightarrow$ Đây là màn hình **CÀI ĐẶT HỢP LỆ**, KHÔNG PHẢI MÀN HÌNH MẤT LOGIN.
- **Quy tắc xử lý trong Automation:**
  - Thêm negative condition cho detector `login`: Khi phát hiện từ khóa "Đăng nhập", nếu màn hình có "Cài đặt và quyền riêng tư" hoặc "Chuyển đổi tài khoản" thì PHẢI coi là Benign Settings Subpage.
  - Phục hồi: Bấm phím Back (KEYCODE_BACK) hoặc tap nút "Quay lại màn hình trước" (`ImageView`) để quay về Profile/Feed tiếp tục quy trình.

---

## 3. Dạng 2: Mismatch Username do TikTok Chỉ Hiển Thị Display Name (M1, M22, M39, M72)

- **Cơ chế lỗi:**
  - Runner đã thực hiện switch account thành công ở đầu session (preflight switch), lướt đủ 18/18 video For You.
  - Đến bước nghiệm thu cuối (`verify_profile`), runner tap vào tab Profile để kiểm tra lại username.
  - Trên TikTok UI bản mới (v46+), thanh tiêu đề Profile chỉ hiển thị Tên hiển thị (*Display Name*, ví dụ M1 hiển thị `Giang Han`) tại `android.widget.TextView [[366,117][720,183]]`.
  - Không có bất kỳ node TextView nào chứa text `@ginnyhanstei80` (username kỳ vọng).
  - Detector tìm kiếm username bằng text exact match thất bại (`detected: null`) $\rightarrow$ ném lỗi `profile verification mismatch: profile account mismatch`.
  - Hậu quả: Feed session bị đánh dấu fail/manual-needed, vô hiệu hóa hook Follow oan, dù tài khoản hoàn toàn khỏe mạnh (hook Upload video sau đó vẫn chạy và post video thành công 100%).
- **Quy tắc xử lý:**
  - Kiểm tra kết quả preflight: Nếu preflight switch đã thành công và tài khoản đã được chọn đúng trong Account Switcher trước khi lướt feed, không được fail-closed gắt gao ở cuối session nếu chỉ thiếu text `@username`.
  - Cho phép so khớp bổ sung qua Display Name / mapping workbook hoặc tap vào vùng chỉnh sửa/menu để trích xuất username chính xác.

---

## 4. Kỷ Luật Coordinator Triage O(1) Khi Nhận Farm Alert:
1. Truy cập trực tiếp `--artifact-root` trong `D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/<row-time>/<timestamp>/`.
2. Đọc `summary.txt` (bảng `blocker_taxonomy_summary`) để phân loại chính xác các nhóm lỗi (proxy, popup, detector miss, mismatch).
3. Đọc log chi tiết `machines/machine_<N>/<timestamp>/log.jsonl` và file `ui.xml` tương ứng.
4. Nghiệm thu ảnh screenshot có sẵn tại `artifacts/.../screen.png` và đính kèm `MEDIA:<path>` theo đúng Gate 6.
