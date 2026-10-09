# Định nghĩa chuẩn Dưỡng Sinh & Quy tắc Anti-Overengineering (Taadaa Farm)

## 1. Bản chất chuẩn của "Dưỡng sinh" trên Taadaa Phone Farm

- **LƯỚT FEED LÀ NỀN TẢNG BẤT BIẾN 100%:** Mọi nick khi vào ca/phiên nuôi ĐỀU LƯỚT FEED để nuôi trust score và IP proxy. Dưỡng sinh KHÔNG PHẢI là lướt feed.
- **Dưỡng sinh (Organic Rest 1/3):** Chính xác là thao tác **TẮT ĐĂNG VIDEO + TẮT FOLLOW** trong ngày nuôi đó (0 follow, 0 upload).
- **Ý nghĩa với nhịp đăng:**
  * **Nick Thường (`NORMAL`):** Có ngày dưỡng sinh 1/3 -> nhịp đăng tự nhiên giãn ra **2.5 – 3 ngày / video** (tiết kiệm video cho nick flop).
  * **Nick Đang Cắn Đề Xuất (`BOOST`):** Vẫn lướt feed bình thường, nhưng **gỡ lệnh cấm upload của ngày dưỡng sinh** -> được phép đăng đều đặn **48h / lần (2 ngày 1 video)** để đón sóng phân phối.
  * **CẤM** tăng lên 1 video/ngày (tránh cannibalization view và spam trigger).

## 2. Cảnh báo Anti-Overengineering (Tránh bẫy lý thuyết suông của LLM Reviewer)

- **CẤM "Quarantine Bất Tử" & "Kiểm tra tay":**
  * Video mới đăng bị 0-view hay vài view là hiện tượng bình thường trên TikTok (do chậm index / lag thống kê).
  * Tuyệt đối CẤM tự ý kích hoạt cờ Quarantine dừng đăng toàn bộ rồi bắt user đi "kiểm tra tay" (manual review). Nick flop/0-view cứ để chạy ở chế độ thường, automation tự xử lý.
- **CẤM "Khóa 1 chiều khi farm có biến":**
  * Không tự ý vẽ thêm các cơ chế khóa/đóng băng toàn farm trừ khi có chỉ thị trực tiếp từ User.
- **Bẫy dao động Dashboard (Flapping "hôm nay cắn mai mất"):**
  * Dashboard delta 24h là sensor, không dùng làm công tắc trực tiếp.
  * Khi nick cắn đề xuất -> gắn cờ `BOOST` khóa giữ 5 ngày (đủ để đăng 2-3 video nhịp 48h), tránh việc ngày hôm sau delta giảm nhẹ làm hệ thống nhảy giật cục về dưỡng sinh.

## 3. Dual Gate Follow (Ngày tuổi >= 21 & Video >= 6)

- **Điều kiện đi follow:** `account_age_days >= 21 VÀ video_count >= 6`.
- **Giai đoạn Mồi (21–30 ngày):** Budget nhẹ 3–5 follow/phiên (Watchdog 2 tầng bảo vệ).
- **Trưởng thành (> 30 ngày & video >= 10):** Full budget theo config máy (10–20 follow/phiên, tuyệt đối không bóp thành 6–10 do nhầm docstring cũ).
- **Cột 5 Safe Workbook:** `taikhoan_run_safe.xlsx` mang cột 5 là `Ngày Tạo` (`_parse_date_iso`), bảo toàn 4 cột đầu cho các script cũ.
- **Code Threading:** `workbook.py` (`RowMapping.account_age_days`) -> `follow_engine.py` -> `mode1_search_follow.py` & `mode2_follow_followers.py` (`state.session_budget(video_count, account_age_days)`).
