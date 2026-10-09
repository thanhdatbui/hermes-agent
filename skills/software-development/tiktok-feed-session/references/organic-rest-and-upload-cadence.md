# Quy định Vận hành: Dưỡng Sinh (Organic Rest), Nhịp Đăng Video & Nick Cắn Đề Xuất

## 1. Định Nghĩa Bất Biến Về "Dưỡng Sinh" (Organic Rest)
- **HIỂU LẦM TAI HẠI CẦN TRÁNH:** Tuyệt đối không được nhầm "dưỡng sinh" là đi lướt feed / xem video.
- **NGUYÊN TẮC CỐT LÕI:**
  - **100% mọi nick khi vào phiên/ca nuôi ĐỀU LƯỚT FEED:** Lướt FYP, xem video, thả tim tự nhiên là nền tảng bắt buộc để duy trì Trust Score và nuôi IP proxy cho thiết bị.
  - **Dưỡng sinh (Organic Rest)** là cơ chế kiểm soát nhịp hành vi: **TẮT UPLOAD và TẮT FOLLOW (0-Upload + 0-Follow)** vào ngày nghỉ dưỡng sinh.
  - **Công thức hiện tại trong code (`multi_machine_feed_session.py`):**
    ```python
    h = hashlib.md5(f"{date_str}:{m_num}:{r_num}".encode("utf-8")).hexdigest()
    is_organic_rest = (int(h[:8], 16) % 3) == 0  # Xác suất 1/3 ngày
    ```

---

## 2. Nhịp Đăng Video Theo Phân Loại Tài Khoản

| Trạng thái Nick | Chế độ Dưỡng Sinh | Nhịp Đăng Video Thực Tế | Mục đích |
| :--- | :--- | :--- | :--- |
| **Nick Thường / Flop (`NORMAL`)** | Bật dưỡng sinh 1/3 (0-Up, 0-Follow) | **2.5 – 3 ngày / 1 video** | Tiết kiệm tài nguyên render, giảm áp lực kho video, tránh bị TikTok gán cờ Spam Creator cho kênh flop. |
| **Nick Cắn Đề Xuất (`BOOST`)** *(Plan đã duyệt)* | **Gỡ bỏ ngày nghỉ Upload** (vẫn lướt feed 100%) | **Cố định 48h / 1 video (2 ngày 1 lần)** | Vét trọn làn sóng phân phối đề xuất của TikTok, giữ đà tương tác liên tục cho video. |

---

## 3. Thực Trạng Codebase Hiện Tại (Đối Soát Production)
- **Tình trạng:** Cơ chế tự động nhận diện nick cắn đề xuất để ưu tiên đăng nhịp 48h **MỚI CHỈ ĐẠT ĐỒNG THUẬN VỀ PLAN/SPEC**, **CHƯA ĐƯỢC CODE VÀO RUNNER**.
- **Hiện thực trong runner (`multi_machine_feed_session.py:3771`):** Mọi nick (kể cả nick đang viral) hiện vẫn áp dụng công thức hash 1/3 nghỉ upload cố định. Chưa có bảng `account_state` trong SQLite `tiktok_tracker.db` để runner đọc và phân luồng đăng.

---

## 4. Chống Bệnh Over-Engineering Khi Thiết Kế Farm Automation
- **Không tự vẽ ra "Quarantine bất tử / Bắt kiểm tra tay khi 0-view":** Video mới tải lên bị 0 view hay ít view là hiện tượng bình thường trên TikTok (do chậm index). Tuyệt đối không chặn đứng lịch đăng hay bắt người vận hành phải duyệt tay thủ công.
- **Không vẽ "Khóa 1 chiều toàn farm":** Các cơ chế lý thuyết suông gây phức tạp hóa hệ thống phải loại bỏ hoàn toàn.
- **Ngân sách Follow khi trưởng thành:** Luôn đọc đúng cấu hình máy (`config/machine*.yaml` — chuẩn farm là 10–20 follow/phiên), không trích dẫn lại comment cũ lỗi thời (6–10).
