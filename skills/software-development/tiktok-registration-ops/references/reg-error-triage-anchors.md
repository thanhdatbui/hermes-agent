# Canonical Registration Error Anchors & Triage (social_reg_v1.py)

Tài liệu tra cứu nhanh các lỗi phổ biến khi chạy Preflight Reg bù hoặc batch `social_reg_v1.py` trên dàn máy Samsung S7 / Android 7.

## 1. Bản Đồ Code Anchors (social_reg_v1.py)

| Lỗi Emitted | Hàm Phụ Trách | Dòng Anchor | Cơ Chế & Nguyên Nhân Cốt Lõi |
|---|---|---|---|
| `[07] Khong the xac dinh trang thai email` | `fill_email_for_stt(...)` | ~3911 | Vòng lặp duyệt candidate emails: sau khi nhập email và bấm "Tiếp tục", màn hình không xuất hiện ô mật khẩu cũng không có text tài khoản đã đăng ký trong thời gian timeout (`had_timeout_error = True`). Toàn bộ emails đều bị timeout mạng/chậm → quăng lỗi. |
| `Lỗi mở account dropdown` (`[03_dropdown] Khong mo duoc account dropdown`) | `open_account_dropdown(...)`<br>Fallback: `_open_account_dropdown_via_settings(...)` | ~3242<br>(fallback ~3178) | Thử mở dropdown qua header selectors (Pass 1-4) thất bại, fallback qua *Menu hồ sơ → Cài đặt và quyền riêng tư → Chuyển đổi tài khoản* thất bại, restart app thử lại vẫn thất bại. Thường do Profile mới chưa đặt tên (không có icon chevron, xem Case REG-22) hoặc bị widget "Bạn đang nghĩ gì..." / màn hình Camera che khuất (Case REG-25). |
| `[01_open] TikTok not foreground after clean launch` | `open_app(..., max_wait=45)` | ~2413 | Khởi chạy TikTok qua monkey/am nhưng sau 45s app không lên foreground. Thường do máy đang tắt màn hình (`screen_state == OFF`), kẹt ở `LauncherActivity`, hoặc dính dialog ANR / crash ("TikTok đã dừng lại") không được dismiss kịp. |
| `[adb-timeout] UI_XML_TIMEOUT` | `_ui_xml_timeout_message(...)`<br>gọi trong `_atx_capture_ui_xml` / `get_ui_xml` | ~906 | Quá thời gian chờ dump UI (15-20s) qua `atx-agent` (port 7912) hoặc shell dump. Nguyên nhân: màn hình tắt, CPU máy S7 bị nghẽn (do số worker chạy đồng thời > 6), hoặc app bị freeze tại SplashActivity. |

## 2. Phân Loại Triage: Lỗi Hạ Tầng/Màn Hình vs Lỗi Giao Diện/Mạng

Khi gặp batch báo lỗi hàng loạt (như tại đợt Preflight Reg bù Row 2 / Row 4):

1. **Nhóm A: Lỗi Hạ tầng & Trạng thái Thiết bị (Infrastructure & Device State)**
   - Biểu hiện: `[01_open]` và `UI_XML_TIMEOUT`.
   - Kiểm tra ngay:
     - `dumpsys power | grep mScreenOn` hoặc `dumpsys window | grep mScreenOn` (màn hình có bị TẮT không).
     - Component đang chiếm focus: `LauncherActivity` hay `com.ss.android.ugc.trill`.
     - Số lượng workers đồng thời (`--max-workers` không được vượt quá 6 theo Case REG-16 để tránh nghẽn switch/ADB daemon).
2. **Nhóm B: Lỗi Giao diện & Mạng trong App (In-App UI & Network State)**
   - Biểu hiện: `[03_dropdown]` và `[07]`.
   - Kiểm tra ngay:
     - Với `[03_dropdown]`: Kiểm tra XML và ảnh chụp `fail_03_account_dropdown.png`. Xem máy có đang dính popup Edit Name, onboarding "Chọn chủ đề", dialog Facebook, hay màn hình Camera "Bạn đang nghĩ gì...".
     - Với `[07]`: Kiểm tra kết nối mạng/proxy trên thiết bị, xem có thông báo "Không có kết nối Internet" hoặc loading spinner quay vô tận khi bấm "Tiếp tục".

## 3. Trường Dữ Liệu Bắt Buộc Ghi Nhận (Evidence Checklist)

Trước khi kết luận nguyên nhân hoặc alert cho runner:
- `screen_state`: Trạng thái bật/tắt màn hình tại thời điểm chạy.
- `mCurrentFocus`: Package và Activity hiện tại.
- `atx_alive`: Kết nối tới cổng 7912 của thiết bị.
- `artifact_paths`: Đường dẫn ảnh `fail_*.png` và file `fail_*.xml` lưu trong `screenshots_social/`.
- `worker_concurrency`: Số worker đang chạy đồng thời (phải $\le 6$).
