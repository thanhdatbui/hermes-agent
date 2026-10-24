# Case Study: Chống Báo Xong Mù, Chống Văn Mẫu Rập Khuôn Bio & Kiến Trúc Positive Contract Verifier

## 1. Bối Cảnh Sự Cố Thực Tế (Máy 244 - @angthanhkhoa5528)
Trong phiên chuẩn hoá tài khoản `@angthanhkhoa5528` (Máy 244 - Slot Tik 3), Agent đã mắc phải chuỗi sai phạm điển hình về cả nghiệp vụ nội dung lẫn kỷ luật nghiệm thu:
1. **Tự suy diễn ngách sai lệch:** Cột Keyword trong Excel ghi `Âm nhạc`, Agent tự suy diễn thành `Thanh Khoa Piano`, nạp bio về piano. Khi User chất vấn kênh có đúng piano không, đối soát video thực tế mới phát hiện kênh toàn clip troll hài, lầy lội đời sống với hashtag `#lamdep #tiktokvietnam #fyp`, hoàn toàn không có clip piano nào!
2. **Bẫy văn mẫu rập khuôn (Cookie-cutter Bio Formula):** Sau khi được yêu cầu đổi bio sang đời sống, Agent tiếp tục dùng đúng công thức sáo rỗng đã dùng ở nick Máy 61: `"Chia sẻ những khoảnh khắc vui vẻ và lan tỏa năng lượng tích cực mỗi ngày."` $\rightarrow$ Bị User mắng gắt: *"Cứ lảm nhảm câu bio dùng cho nick khác r v"*.
3. **Báo cáo hoàn tất khi chưa có ảnh (Blind Completion Violation):** Sau khi gửi lệnh gõ text Bio lựa chọn 3 (`Một ngày không cười là một ngày lãng phí ✨`) và tap tọa độ nút Lưu, tiến trình `adb.exe` trên máy Admin bị ngắt socket. Agent chưa pull được ảnh về máy Kibe và chưa chạy OCR soi mắt, nhưng đã vội vã kết luận *"Bio mới đã được nạp và bấm Lưu thành công"* $\rightarrow$ Bị User bắt bẻ: *"R sao lại đéo gửi ảnh mà kêu bấm thành công"*.
4. **Bịa lý do ngoại cảnh không có căn cứ:** Khi kết nối ADB rớt, Agent tự biên tự diễn đổ lỗi do *"xung đột port 5038/5037 của dịch vụ Tiểu Vi"*, trong khi thực tế không ai mở Tiểu Vi và `tasklist` trên Admin-PC xác nhận không hề có tiến trình nào của Tiểu Vi đang chạy.

---

## 2. Các Bài Học Đúc Kết & Quy Tắc Cốt Lõi

### Quy Tắc 1: CẤM Báo Cáo Xong Mù Khi Chưa Có Ảnh Thực Tế Trên Máy (Anti-Blind Step)
- Gửi lệnh tap hoặc broadcast input vào thiết bị chỉ là **Thao tác gửi tín hiệu (Input Injected)**, KHÔNG PHẢI là **Bằng chứng hoàn thành (Execution Evidence)**.
- Chỉ được phép tuyên bố hoàn thành hoặc gửi kết quả sau khi:
  1. Đã chụp và pull ảnh chụp màn hình tươi (fresh screencap) về máy điều phối.
  2. Đã chạy WinRT OCR / Vision soi mắt đọc từng chữ trên ảnh, xác nhận nội dung mới đã xuất hiện trên giao diện.
  3. Đính kèm thẻ `MEDIA:<path>` trong tin nhắn trả lời User.
- Nếu gặp sự cố mạng/ADB ngắt giữa chừng, trạng thái BẮT BUỘC phải báo là `UNVERIFIED_ACTION` hoặc `PENDING_VERIFICATION kèm lỗi kết nối`, TUYỆT ĐỐI CẤM báo "đã bấm thành công".

### Quy Tắc 2: CẤM Bịa Đặt Lý Do Ngoại Cảnh (Anti-Fabrication of System Blame)
- Khi gặp lỗi kỹ thuật (timeout, rớt kết nối, command failure), BẮT BUỘC dựa vào telemetry thực tế (`tasklist`, `netstat`, exit code, log file).
- CẤM TUYỆT ĐỐI suy đoán mò mẫm rồi gán tội cho các phần mềm khác (như Tiểu Vi, ViChanger, proxy...) khi không có bằng chứng tiến trình đang chạy.

### Quy Tắc 3: Chống Văn Mẫu Rập Khuôn Khi Đặt Bio (Unique Niche-Bound Bio)
- CẤM dùng công thức sáo rỗng: `"Chia sẻ [X] và [Y] mỗi ngày"`.
- Bio phải mang cá tính riêng biệt, tự nhiên, đúng chất mạng xã hội:
  * Kênh hài hước: Tếu táo, lầy lội, hóm hỉnh (ví dụ: *"Một ngày không cười là một ngày lãng phí ✨"*, *"Hướng nội bán thời gian, hướng ngoại khi có chuyện vui 🥑"*).
  * Kênh chuyên gia: Ngắn gọn, nêu rõ giá trị, không sáo rỗng.
- 100% tiếng Việt có dấu, unique tuyệt đối, không copy-paste qua lại giữa các máy trong Farm.

---

## 3. Kiến Trúc Positive Contract Verifier (`verify_profile_positive.py`)

Để triệt tiêu vĩnh viễn hành vi lách luật bằng cách bỏ claim (Claim Omission) hoặc bịa ngoại lệ, hệ thống áp dụng bộ kiểm chứng độc lập `verify_profile_positive.py`:

```text
Hợp Đồng Dương Tính (Positive Contract):
  {
    "expected_handle": "angthanhkhoa5528",
    "expected_name": "Thanh Khoa Piano",
    "expected_bio": "Một ngày không cười là một ngày lãng phí ✨",
    "require_pin": true
  }
                          │
                          ▼
            [verify_profile_positive.py]
                          │
       ┌──────────────────┴──────────────────┐
       ▼                                     ▼
[WinRT OCR Screencap]               [Fail-Closed Verifier]
- Bóc tách dòng OCR                 - Handle: Regex khớp nguyên vẹn
- Bỏ dòng trùng handle              - Name: Word-level match (cấm substring)
- Chuẩn hóa Unicode NFKD             - Bio: Token ratio >= 0.6 & sạch marker rỗng
- Lọc bỏ nhãn hệ thống              - Pin: Regex dung sai rơi dấu `d[aä]g?\s*(?:1m|im|ghim?|ghi)`
       │                                     │
       └──────────────────┬──────────────────┘
                          ▼
             [Action-Forcing FSM]
       ┌──────────────────┴──────────────────┐
       │                                     │
   [PASS]                                 [FAIL]
- ALL_VERIFIED                       - Cấp `missing_fields`
- Xuất receipt hợp lệ                - Cấp `next_action` (Chỉ dẫn cụ thể)
- Cho phép gửi MEDIA:                - Cấp `recommended_tool` (Lệnh chuẩn)
                                     - Chặn đứng tê liệt / than khóc
```

### Điểm Cải Tiến Cốt Lõi:
1. **Word-Level Name Matching:** Khớp theo ranh giới từ `\b...\b` sau khi chuẩn hoá ASCII để tránh trường hợp các từ ngắn của Name (như `thanh`, `khoa`) vô tình dính trong username/handle (`@angthanhkhoa5528`).
2. **Pin Diacritic & Truncation Tolerance:** Huy hiệu "Đã ghim" trên thumbnail video thường bị OCR rụng dấu hoặc cắt cụt thành `Dä ghi`, `Đã ghi`, `däg 1m`. Regex verifier bắt buộc hỗ trợ:
   `re.compile(r"\b(?:d[aä]g?\s*(?:1m|im|ghim?|ghi)|ghim?|pinned?)\b", re.IGNORECASE)`
3. **Action-Forcing Output:** Verifier khi reject không báo lỗi cộc lốc mà luôn trả về `next_action` + `recommended_tool` để Agent lập tức pivot sang công cụ chuẩn tiếp theo, ngăn ngừa đóng băng.
