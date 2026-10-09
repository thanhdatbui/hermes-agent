# QUY CHUẨN THIẾT KẾ WATCHDOG & BÁO CÁO ĐỊNH KỲ (CHỐNG SPAM ALERT)

## 1. BỐI CẢNH & NGUYÊN TẮC CỐT LÕI
Người dùng cực kỳ dị ứng với việc nhận các tin nhắn tự động vụn vặt, spam thông báo khi hệ thống tự phục hồi thành công. Mọi tác vụ giám sát và báo cáo (kể cả cronjob cũ lẫn script/watchdog mới tạo) bắt buộc phải tuân theo sự phân định rạch ròi giữa **Tác vụ Tự phục hồi ngầm (Auto-Healer / Maintenance)** và **Báo cáo Tổng hợp Định kỳ (Summary Report)**.

---

## 2. PHÂN ĐỊNH 2 NHÓM TÁC VỤ VÀ YÊU CẦU KỸ THUẬT

### Nhóm 1: Auto-Healer / Maintenance / Sync Watchdog
*(Ví dụ: cài app bù cho máy thiếu, dọn device locks mồ côi, auto-healer Wi-Fi/ADB transport, chuẩn hóa timeout màn hình, dọn cache, kích hoạt tài khoản DB nội bộ...)*

* **Cấu hình `deliver`:** **BẮT BUỘC `deliver: "local"`**. CẤM TUYỆT ĐỐI gán `deliver: "origin"` hay `deliver: "telegram:..."`.
* **Cơ chế Silent Watchdog (`no_agent: true`):**
  - Trong runtime của Hermes, hễ script in bất kỳ ký tự nào ra `stdout`, hệ thống sẽ tự động bọc lại và bắn tin nhắn Telegram tới target.
  - Khi script chạy bình thường (không có gì cần sửa) HOẶC khi script tự động sửa/cài đặt/phục hồi thành công: **BẮT BUỘC ghi log ngầm vào file** (ví dụ `D:\Taadaa\runtime\<job_name>.log`), **`stdout` BẮT BUỘC RỖNG 100% (`sys.exit(0)`)**.
  - **CẤM print() thông báo hoàn thành**: Việc tự động vá lỗi là nghiệp vụ nền thường quy, không được coi là sự kiện cần đánh động con người.
  - **Chỉ in ra `stdout` khi:** Gặp lỗi nghiêm trọng (`errors` / exception) mà script không thể tự giải quyết, cần người can thiệp.
* **Tần suất chạy (`schedule`):**
  - Tránh đặt tần suất quá dày (`*/5 * * * *`) cho các tác vụ kiểm tra nặng (như quét toàn bộ 150+ máy qua ADB để đối soát APK).
  - Giãn lịch về khung giờ bảo trì cuối ngày (ví dụ `0 4 * * *`) hoặc giữa các ca nuôi.

### Nhóm 2: Scheduled Summary Report (Báo cáo Định kỳ)
*(Ví dụ: tổng kết ca nuôi acc TikTok, báo cáo tiến độ render/download video 6h, báo cáo trạng thái OAuth pool 6h, báo cáo farm sáng 07:00, backup tuần...)*

* **Cấu hình `deliver`:** Gửi đúng kênh đích chỉ định (ví dụ `telegram:-5373649734` cho Farm Alert).
* **Định dạng Chuẩn hóa (Standardized Schema):**
  - **Header chuẩn:** `[TÊN BÁO CÁO - KHUNG GIỜ / CA / NGÀY]`
  - **Số liệu tổng hợp (Aggregated Metrics):** Tổng số | Thành công (✓) | Thất bại (✗) | Tỷ lệ %.
  - **Gom nhóm cô đọng:** Danh sách máy/tài khoản thành công hay thất bại gom nhóm ngắn gọn, có phân loại nguyên nhân chính.
  - **CẤM xả raw log / raw command output / dump chi tiết vụn vặt.**
* **Khung giờ chạy:**
  - Chỉ chạy đúng vào các mốc kết thúc ca (sau ca sáng/trưa/tối) hoặc chu kỳ 6h/12h/hàng ngày theo quy hoạch.

---

## 3. CHECKLIST TRƯỚC KHI TẠO HOẶC SỬA WATCHDOG / CRONJOB
1. [ ] Đã xác định rõ tác vụ thuộc **Nhóm 1 (Ngầm)** hay **Nhóm 2 (Báo cáo)** chưa?
2. [ ] Với Nhóm 1: `deliver` đã đặt `local` chưa?
3. [ ] Với Nhóm 1: Nhánh tự sửa thành công đã gọi `sys.exit(0)` với `stdout` rỗng và ghi log file chưa?
4. [ ] Với Nhóm 1: Đã xóa toàn bộ các lệnh `print()` thông báo kết quả thành công chưa?
5. [ ] Tần suất `schedule` có hợp lý và tránh nghẽn hạ tầng USB/ADB không?
6. [ ] Với Nhóm 2: Báo cáo đã đạt chuẩn cô đọng, có số liệu % và không xả log chi tiết chưa?
