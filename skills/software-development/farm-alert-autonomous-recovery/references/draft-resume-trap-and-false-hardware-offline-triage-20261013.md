# Triage: Bẫy Quy Kết Nhầm Phần Cứng & Bug "Draft Resume Trap" Gây Stale Upload (13/10/2026)

## 1. Bối Cảnh Sự Cố & Bài Học Điều Phối (User Correction)
- **Hiện tượng:** Watchdog `daily-stale-upload-accounts-watchdog` báo cáo 108 nick bị đóng băng > 14 ngày (trong đó có M10, M13, M19, M44, M55, M69, M74...).
- **Sai lầm chẩn đoán của Agent:** Kiểm tra `adb devices` thấy một số máy rớt USB (offline) $\rightarrow$ Vội vàng kết luận *"Máy 10, 44, 55, 69 kẹt nick hơn 20 ngày là do offline phần cứng mất kết nối USB/ADB"*.
- **Phản hồi chỉnh đốn của User:** *"Mấy máy kibe bị off phần cứng đó là vừa bị đây thôi đéo có chuyện hơn 20 ngày bị"*.
- **Bằng chứng thực tế sau đối soát:**
  * Các máy đó (M44, M55, M69, M13, M19) **hoàn toàn online và chạy đều đặn mỗi ngày**.
  * Trên cùng một máy, **7/8 slot vẫn đăng video ầm ầm** (Tik 1: 33 clip, Tik 2: 18 clip, Tik 3: 13 clip, Tik 4: 12 clip...).
  * Việc rớt ADB chỉ là hiện tượng nghẽn bus EHCI tạm thời sau 24h chạy liên tục, tự phục hồi sau chu kỳ auto-reboot định kỳ 11:35 trưa.
  * Chỉ có DUY NHẤT 1 slot cụ thể trên máy bị kẹt ngày đăng clip.

## 2. Invariant Chẩn Đoán: Phân Biệt "Máy Offline Tức Thời" vs "Slot Kẹt Logic"
- **CẤM TUYỆT ĐỐI:** Lấy thời điểm máy rớt ADB tức thời để quy chụp nguyên nhân nick bị kẹt dài ngày (> 14 ngày).
- **Quy trình Triage 3 bước bắt buộc:**
  1. **Kiểm tra đa slot trên cùng máy:** Truy vấn `snapshots` trong `D:\Taadaa\data\tiktok_tracker.db` hoặc đọc `taikhoan_run_safe.xlsx` để xem các slot khác (Tik 1..8) của máy đó có tăng clip trong 1–7 ngày qua không.
  2. **Nếu các slot khác vẫn tăng clip:** $\rightarrow$ Khẳng định 100% phần cứng máy BÌNH THƯỜNG. Lỗi khu trú tại riêng tài khoản/workflow của slot bị kẹt.
  3. **Đọc `execution.log` & `checkpoint.json` của slot bị kẹt:** Truy vết thư mục run gần nhất tại `D:\CodexRuntime\tiktok-video\runs\run_<serial>_*` để xác định chính xác state máy bị văng (`MANUAL_REVIEW`, UI blocker, hay crash).

---

## 3. Bản Chất Bug "Draft Resume Trap" (Bẫy Kẹt Bản Nháp)
*(Gây kẹt vĩnh viễn cho M44 Tik 5, M21 Tik 7... kéo dài > 20 ngày)*

### 3.1. Cơ chế lỗi trong `state_machine.py`
1. Khi tài khoản TikTok vô tình có 1 bản nháp cũ lưu trên profile, `ACCOUNT_READY` gắn cờ `self.context.has_profile_draft = True`.
2. Khi vào state `VIDEO_PICK`: Script kích hoạt `_resume_draft_from_profile(adapter, xml_text)`.
3. Script tap mở bản nháp nhưng **không vào được Composer** (`COMPOSER_NOT_CONFIRMED`). Hàm trả về `False`.
4. Script in log: `[VIDEO_PICK] Mở bản nháp không thành công; tiếp tục fallthrough luồng upload chuẩn`.
5. **Điểm chết người:** Khi fallthrough, màn hình điện thoại **vẫn đang kẹt trong thư viện bản nháp hoặc editor bản nháp**, không có thanh điều hướng Home với nút `[+]` (Quay).
6. Script cố gắng tìm nút tạo video `[+]` $\rightarrow$ Thất bại $\rightarrow$ Văng lỗi:
   `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`
7. Workflow dừng ở `MANUAL_REVIEW`, không đăng được clip.
8. Ở các ca nuôi tiếp theo (cách nhau 96h theo chu kỳ 4 ngày), bản nháp vẫn nằm nguyên trên profile $\rightarrow$ **Lặp lại lỗi y hệt và kẹt vĩnh viễn**.

### 3.2. Giải pháp kỹ thuật chuẩn hóa
Ngay sau khi `_resume_draft_from_profile` trả về `False`:
```python
if not self._normalize_to_home_for_video_pick(adapter, adapter.dump_ui()):
    logger.error("[VIDEO_PICK] Không thể trở về Home sau khi mở bản nháp thất bại")
    return False
xml_text = adapter.dump_ui()
```
* Bắt buộc dùng `_normalize_to_home_for_video_pick` để bấm `Back` thoát sạch các subpage/thư viện nháp, đưa app về màn hình **Trang chủ** có nút `[+]` được kiểm chứng visual gate trước khi tiếp tục luồng upload chuẩn.
* Kiểm tra và dọn dẹp các bản nháp hỏng trên profile bằng `_delete_all_profile_drafts` nếu resume liên tục thất bại.
