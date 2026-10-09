# Tỉ lệ Like Feed & Phân Biệt Lỗi Đăng Video Batch

## 1. Tỉ lệ Like (Thả tim) khi Lướt Feed

### Thiết kế chuẩn
- **Mục tiêu**: Tái tạo hành vi người xem thật (casual viewer), tạo Trust Score tự nhiên, tránh bị thuật toán gắn cờ bot zombie (0 like) nhưng cũng không spam like liên tục để tránh bị action-block / shadowban.
- **Cấu hình gốc (`python_runner/flows/feed_swipe_smoke.py`)**:
  - `DEFAULT_LIKE_RATE_PERCENT = 10`
  - `DEFAULT_FEED_LIKE_RATES`:
    - Tab Đề xuất (`for-you`): **8%**
    - Tab Đang theo dõi (`following`): **50%**
    - Tab Bạn bè (`friends`): **80%**
- **Cơ chế Fast Swipe xen kẽ Deep Inspect**:
  - Cứ **2–4 video lướt nhanh** (2.0–5.0s, vuốt ADB trực tiếp, KHÔNG dump XML, KHÔNG like).
  - Có **1 video Deep Inspect** (xem lâu 12–25s, dump XML, tỉ lệ like tại nhịp này nâng lên **40%** để bù).
- **Số liệu đo đạc thực tế toàn Farm (80 máy)**:
  - Mỗi phiên máy lướt 16–22 video (max 28 swipes).
  - Tổng tỉ lệ like toàn phiên đạt **~15% – 18%** trên tổng số lượt vuốt.
  - Trung bình mỗi máy thả **2 đến 4 like / phiên**.
  - **Kết luận**: Tỉ lệ like hiển thị trên báo cáo watchdog (khoảng 190–210 like / 1.200 swipes toàn farm) là **ĐÚNG 100% THEO THIẾT KẾ**, không được tự ý can thiệp đẩy cao hơn.

---

## 2. Phân Tích & Phân Biệt "Lỗi" Đăng Video Trong Batch

Khi nhận báo cáo watchdog hoặc người dùng thắc mắc "sao script đăng video lỗi nhiều vậy", điều phối viên CẦN PHÂN TÁCH RÕ RÀNG giữa:

### A. Nhóm BỎ QUA THEO THIẾT KẾ (Không phải lỗi — chiếm phần lớn)
1. **`skipped: organic-rest-day-no-upload` (~20–25 máy / batch 80 máy)**:
   - Cơ chế **Dưỡng sinh ngẫu nhiên 1/3 (Organic Rest 1/3)**:
     ```python
     h = hashlib.md5(f"{date_str}:{m_num}:{r_num}".encode("utf-8")).hexdigest()
     return (int(h[:8], 16) % 3) == 0
     ```
   - Mỗi ngày ~33% tài khoản được xác định nhất quán chỉ lướt feed nuôi, **tuyệt đối 0 follow và 0 upload** để xóa dấu vết botnet và hồi phục Trust Score.
   - Watchdog ghi nhận máy thuộc diện này là `skipped`, hoàn toàn không phải script bị crash.
2. **`skipped: already_uploaded_in_shift` (Phiên 2)**:
   - Theo cơ chế Opportunistic Upload & Sổ cái nguyên tử `_ShiftUploadLedger` (Case 152): Máy đã đăng thành công ở Phiên 1 thì sang Phiên 2 sẽ tự động Safe-Skip ngay trong 0.1s để đảm bảo tuyệt đối 1 ca chỉ đăng tối đa 1 video.
3. **`skipped: missing_account_id`**: Máy chưa được gán nick hoặc dòng trống trong workbook safe.

---

### B. Nhóm LỖI THỰC SỰ CẦN XỬ LÝ
1. **`[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING`**:
   - Khi mở popup Chuyển tài khoản trên app TikTok, không tìm thấy tên nick tương ứng với Row trong danh sách.
   - *Nguyên nhân*: Nick bị văng (logout), bị checkpoint/ban nên mất khỏi app, hoặc username hiển thị trên app lệch so với file Excel. Cần kiểm tra và đăng nhập lại nick.
2. **`[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok` (Xung đột đọc/ghi đồng thời trên Excel)**:
   - *Hiện tượng*: Nhiều máy bị lỗi này đồng loạt trong cùng một khoảng thời gian ngắn (2–3 phút) khi đang có nhiều worker khác hoàn thành upload.
   - *Nguyên nhân gốc*: `atomic_workbook_update` chỉ lock khi GHI (`update_video_number`). Trong khi đó, các worker khác gọi `_read_row_from_xlsx()` đọc trực tiếp file `.xlsx` mà không có read-lock. Khi openpyxl đọc trúng lúc file tạm đang được replace/sync trên OneDrive, dữ liệu XML bị dở dang, dẫn đến header `ID TikTok` bị đọc thành `None` và kích hoạt lỗi validation.
   - *Khắc phục*: File sau khi ghi xong sẽ bình thường trở lại (preflight lại sẽ pass). Cần cơ chế retry với jitter/backoff khi đọc workbook nếu gặp lỗi missing fields này.
3. **Lỗi UI màn hình đăng (`VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`, `VIDEO_PICK_HOME_NOT_REACHED`)**:
   - Do TikTok bị mất focus, văng popup quảng cáo/onboarding che khuất thanh điều hướng dưới đáy (Home / Nút Tạo +), hoặc máy bị lag quá thời gian budget 60s.
