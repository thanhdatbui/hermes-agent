# Autonomous AI Auto-Recovery Gemini 3.7 Flash & Follow Cooldown Per-Account Rules (19/08)

## 1. XÓA BỎ HOÀN TOÀN FALLBACK HARDCODE TRONG AI RECOVERY
- **CẤM TUYỆT ĐỐI** dùng `_FALLBACK_RESULT` hoặc bất kỳ mẫu câu/hành động hardcode ("Đã gửi phím Back để đóng màn hình", "Dừng phiên bất thường").
- Mọi chẩn đoán, hướng sửa và hành động (`action_type`, `action_args`) **BẮT BUỘC** phải trích xuất 100% từ phân tích trực tiếp của mô hình Vision (`ag/gemini-3.7-flash-high`).
- Nếu AI không phản hồi hoặc không phân tích được:
  - Trả về `_EMPTY_DECISION` với `action_type = "none"`.
  - **GIỮ NGUYÊN HIỆN TRƯỜNG**, không tự ý bấm Back / Home mù quáng làm mất dấu vết lỗi.

## 2. FIX PARSE JSON MARKDOWN & ĐỌC KEY .ENV TRONG VISION CLIENT
- **Làm sạch Markdown Codeblock**: Khi Gemini 3.7 Flash trả về nội dung dạng ````json { ... } ````, phải strip sạch ```` ```(?:json)? ```` trước khi regex trích xuất JSON.
- **Lọc Comment khi đọc .env**: Phải kiểm tra `if line.strip().startswith("#"): continue` để tránh đọc trúng dòng comment (ví dụ `# OPENROUTER_API_KEY=`) ở đầu file `.env` dẫn đến trả về rỗng và báo thiếu API key giả.

## 3. PHÂN BIỆT RẠCH RÒI LỖI NHẢ FOLLOW VS LỖI ĐIỀU HƯỚNG
- **Lỗi Nhả Follow thật (`FOLLOW_FAILED`)**: Đã tìm đúng nick, đã bấm nút "Follow", nhưng khi vuốt pull-to-refresh kiểm tra lại thì nút bị trả về trạng thái ban đầu ("Follow" / "Follow lại").
  - **Chỉ áp dụng Cooldown cho lỗi này**.
- **Lỗi Điều hướng / Mạng / Giao diện (`MANUAL_REVIEW` / Navigation Fail)**:
  - Mở app chậm, không tìm thấy ô search, giao diện TikTok lạ... **Hoàn toàn KHÔNG phải do TikTok nhả follow hay chặn nick**.
  - **TUYỆT ĐỐI CẤM** gán cờ `follow_failed` để tránh chặn nhầm các phiên sau.

## 4. QUY TẮC COOLDOWN NHẢ FOLLOW THEO TỪNG NICK RIÊNG BIỆT
- State file phân tách theo từng nick: `follow_state_{machine}_row_{account_row_index}.json`.
- Khi một nick bị nhả follow:
  - Script lập tức `break` dừng phiên follow của nick đó ngay tại chỗ.
  - Ghi nhận `follow_failed_date = "YYYY-MM-DD"`.
  - Các phiên sau trong cùng ngày của **RIÊNG nick đó** sẽ tự động BỎ QUA bước Follow, chỉ lướt Feed nuôi.
  - **CÁC NICK KHÁC TRÊN CÙNG MÁY ĐÓ VẪN CHẠY FEED VÀ FOLLOW BÌNH THƯỜNG**, không bị chặn chéo.
- Tự động reset trạng thái khi bước sang ngày mới (00:00).

## 5. WORKFLOW CRON NUÔI ACC KHÉP KÍN & UPLOAD HOOK PHIÊN CUỐI
1. **Ca Nuôi (3 Ca/ngày)**: Mỗi ca gồm 3 phiên lướt (`session_index` = 1, 2, 3).
2. **Feed Session Smoke**: Phân bổ 3 Tab (FYP 85%, Following 8%, Friends 7%) + Watch delay + Tự vượt popup in-app.
3. **Follow Hook**: Kiểm tra Cooldown theo nick -> Nếu OK thì chạy follow chéo; nếu dính nhả follow -> Dừng ngay lập tức và cách ly nick đó trong ngày.
4. **Upload Hook**: Kích hoạt tại phiên cuối của ca (`session_index == 3`), đọc `TikN.xlsx`, kiểm tra `folder_video` và file video render sẵn (`posted_count + 1`) -> gọi `tiktok-video` đăng bài -> Dọn app về Home.
