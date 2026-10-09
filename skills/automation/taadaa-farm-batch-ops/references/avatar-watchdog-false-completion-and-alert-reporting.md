# Avatar Watchdog False-Completion Trap & Farm Alert Reporting Invariant (2026-09-13)

## 1. Bẫy False-Completion trong Watchdog Cron (State Increment Trap)
- **Triệu chứng**: Cron job tự động in ra `[ALL_DONE] Đã hoàn thành toàn bộ avatar cho các Row` và gửi về chat Telegram, trong khi thực tế trên đĩa và workbook chưa có bất kỳ máy nào được chạy thành công (`Avatar = None`).
- **Nguyên nhân gốc rễ**:
  1. Trong script watchdog, việc gọi subprocess (`powershell.exe ... run_tiktok_upload_avatar.ps1`) bị blocking và timeout hoặc fail giữa chừng.
  2. Logic ghi state đặt lệnh chuyển index (`state["current_index"] += 1`) nằm ngay sau subprocess mà không qua bước kiểm tra nghiệm thu thực tế (`summary.csv` hoặc verify cột `Avatar == "OK"` trong workbook).
  3. Khi cron tick định kỳ (mỗi 10-15 phút), state mù quáng tăng từ 0 -> 4, dẫn tới việc script tưởng rằng tất cả các batch đã hoàn thành và gửi báo cáo khống ("xạo l** all done").

## 2. Quy tắc Thiết kế Watchdog Canh Rảnh & Batch Upload
1. **Tuyệt đối không dùng blocking `subprocess.run()` dài hạn trong cron tick**:
   - Khởi chạy batch bằng background detached (`subprocess.Popen` kèm `CREATE_NO_WINDOW`, `close_fds=True`).
   - Lưu trạng thái `running_batch: {tik: N, start_time: T, machines: [...]}` vào file state.
2. **Chỉ chuyển Row khi ĐÃ CÓ BẰNG CHỨNG THỰC TẾ**:
   - Ở các nhịp tick tiếp theo, kiểm tra xem process batch còn sống hay không.
   - Khi process kết thúc, BẮT BUỘC đọc trực tiếp từ `summary.csv` của folder `batch-runs` mới nhất và đối soát lại với workbook (`get_unuploaded_machines(tik)`).
   - Chỉ dọn `running_batch` và chuyển sang Tik tiếp theo khi đã có kết quả thực tế.
3. **Quy chuẩn Báo Cáo Tiến Độ vào Farm Alert (User Rule 2026-09-13)**:
   - **Kênh nhận tin**: Telegram group Farm Alert (`-5373649734`).
   - **Thời điểm gửi tin**: **CHỈ BÁO CÁO KHI CHẠY XONG**, tuyệt đối KHÔNG gửi tin spam lúc bắt đầu chạy.
   - **Nội dung tin báo**:
     + Thời gian hoàn thành & thời lượng chạy.
     + Tổng số acc cần up của Row đó.
     + Danh sách các máy thành công (`Avatar = OK`).
     + Danh sách các máy chưa hoàn tất (để tiếp tục vét hoặc kiểm tra thủ công).

## 3. Quản lý Mở Rộng Farm Tik7 & Tik8 (Keyword / Hashtag Decoupling)
- Khi farm mở rộng lên 8 nick/máy (Slot 7 & Slot 8):
  - Dải nguồn: Tik7 (`481..560`), Tik8 (`561..640`).
  - Dải render: Tik7 (`(m-1)*8+7`), Tik8 (`(m-1)*8+8`).
- **Bẫy thiếu Keyword / Hashtag khi chưa tải xong video gốc**:
  - Downloader có thể chưa tải xong hoặc chưa phân bổ niche cho toàn bộ 80 folder nguồn của Slot 7/8.
  - **Giải pháp chuẩn hóa**:
    1. Khởi tạo trước khung workbook `Tik7.xlsx` và `Tik8.xlsx` đủ 80 máy, đồng bộ ID nick đã reg từ `taikhoan_dat_v2_updated .xlsx` để phục vụ nuôi feed và up avatar.
    2. Những folder đã có niche trong `state.db` -> Điền keyword và hashtag pool chuẩn.
    3. Thiết lập cron auto-sync (`sync-tik-keywords-cron`): định kỳ đọc `state.db` bảng `folders`, khi downloader tải xong và gán niche mới -> tự động tra `niches_pool.txt` sinh hashtag và cập nhật vào workbook mà không ghi đè tiến độ upload/avatar.
