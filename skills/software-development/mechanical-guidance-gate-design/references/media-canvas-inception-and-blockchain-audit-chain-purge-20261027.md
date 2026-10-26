# Media Canvas Inception & Blockchain Audit Chain Purge (2026-10-27)

## 1. Sự Cố Canvas Text Inception (Lỗ hổng "Tự in chữ tự bảo lãnh")
- **Nguyên lý lỗ hổng:** Hook `guard_media_vision_gate.py` cũ đối soát `Claims in Message ⊆ Tokens in OCR`. Agent tự sinh ảnh Canvas đề xuất, dùng `cv2.putText` vẽ chữ lên ảnh, sau đó chạy WinRT OCR quét lại chữ vừa vẽ để lấy receipt PASS.
- **Điểm mù:** OCR chỉ đọc text bề mặt, hoàn toàn mù nội dung pixel thực tế (không phân biệt được vườn cây hay vi sinh vật).
- **Khắc phục O(1):**
  - CẤM dùng OCR text làm bằng chứng cho ảnh visual/proposal/avatar.
  - Chốt chặn nhị phân O(1): Kiểm tra trực tiếp sự kiện `tool_called == "browser_vision"`. Coordinator bắt buộc phải mở ảnh thật ra soi mắt trước khi được gắn thẻ `MEDIA:`.
  - CẤM đẻ thêm VLM ngoại vi (Sol Web :20129 hay Claude CLI) gây trễ và lỗi 503 khi Coordinator đã có sẵn native vision.

## 2. Khai Tử "Blockchain Log Cục Bộ" (Audit Chain Theater)
- **Nguyên lý lỗi:** `closeout_gate.py` bắt buộc mỗi dòng log trong `gate_audit.jsonl` phải chứa SHA-256 chuỗi (`prev_chain_hash` + `self_hash`). Khi một tool khác ghi log JSON chuẩn thiếu `self_hash`, toàn bộ pipeline bị văng `RuntimeError: Corrupted or unreadable audit chain` và sập toàn bộ gate.
- **Bản chất over-engineering:** Băm chuỗi SHA-256 chống sửa đổi trên một máy tính cá nhân đơn quyền User là Security Theater vô nghĩa.
- **Kỷ luật chuẩn:**
  - File log chỉ dùng để ghi nhận (Observability) và truy vết, cấm đặt ràng buộc cryptographic chain làm sập luồng chính.
  - Khi đọc log cũ, nếu thiếu hash thì fallback về GENESIS hoặc bỏ qua, tuyệt đối cấm throw fatal exception.

## 3. Dọn Dẹp safe_push.py & Pre-Push Hooks
- **Bệnh over-engineering cũ:** Bắt buộc `safe_push.py` và `.git/hooks/pre-push` phải duyệt ngược file log `gate_audit.jsonl` tìm bản ghi `APPROVED` trong 30 phút, so khớp commit SHA, scope hash, grace band... Đẻ ra 2 tầng kiểm tra hành chính chồng lấn nhau trên cùng một file log.
- **Chuẩn O(1) mới:**
  - `safe_push.py` chỉ làm nhiệm vụ kỹ thuật: bọc lệnh `git push` an toàn, bỏ hoàn toàn việc đọc log JSONL.
  - Pre-push hook chuyển về kiểm tra kỹ thuật trực tiếp: `py_compile` và `pytest` tập trung cho các file code thay đổi.

## 4. Bảo Tồn Watchdog Giám Sát Hành Vi Farm
- **Quy tắc phân định:**
  - **GIỮ NGUYÊN Watchdog:** `gate_compliance_watchdog.py`, `with_device_lock.py`, `guard_android_proxy.py`, `guard_scan` phải giữ 100% để giám sát hành vi Agent (phát hiện gọi sai tool, quét đĩa diện rộng, bảo vệ an toàn 80 máy Android).
  - **XÓA BỎ Gate ảo tưởng:** DACL memory Windows, HMAC tự ký tự duyệt, AI chấm điểm văn học 85/100, chuỗi băm blockchain log.
