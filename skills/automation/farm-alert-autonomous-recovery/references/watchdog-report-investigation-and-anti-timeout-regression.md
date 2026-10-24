# Kỷ Luật Điều Tra Hiện Trường Khi Nhận Báo Cáo & Chống Regression Vòng Lặp Timeout

## 1. Mệnh Lệnh Điều Tra Thay Vì Diễn Giải Báo Cáo
- Khi User ném/forward một bản tin báo cáo nuôi acc (Cronjob Response, Feed Watchdog, Batch Alert) vào chat:
  + CẤM diễn giải lại, tóm tắt chữ hoặc phân trần lý thuyết suông.
  + BẮT BUỘC coi đó là LỆNH ĐIỀU TRA KỸ THUẬT NGAY LẬP TỨC.
  + Đọc ngay `run_manifest.json` và `log.jsonl` tại thư mục live session.
  + Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` trên máy lỗi đại diện để lấy hiện trường ADB thật.
  + Phân biệt rõ: Mất phần cứng thật (`device not found`) vs Rớt giả do Code Preflight (máy vẫn online) vs Kẹt UI/App. Thấy bug code tự giác L1/L2 fix ngay.

## 2. Invariant Chống Bẫy Vòng Lặp Timeout ADB (Anti-Regression: Case 162)
- Tuân thủ Case 162: ADB Client bắt buộc giữ `connection_wait_timeout = 20.0s` và retry attempts = 3.
- CẤM TUYỆT ĐỐI hạ timeout ADB trên worker con với lý do "ngâm lâu", vì sẽ phá hủy cơ chế tự phục hồi khi USB hub bị micro-drop (sụt tải tức thời 5-10s), gây ra hiện tượng sập batch hàng loạt cho các máy sống.
- Máy mất điện hẳn bị ngâm tới deadline 50 phút là cơ chế fail-closed an toàn của hệ thống, không phải lỗi của timeout ADB. Cần can thiệp phần cứng, cấm chữa sai bằng phần mềm.
