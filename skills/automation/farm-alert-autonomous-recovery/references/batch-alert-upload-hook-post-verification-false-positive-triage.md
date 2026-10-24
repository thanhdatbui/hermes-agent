# Batch Alert: UploadHook Post Verification Inconclusive/Timeout False Positive Triage

## 1. Triệu Chứng & Mẫu Cảnh Báo (Symptom & Alert Pattern)
Khi nhận được cảnh báo batch trên Farm:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN / KIBE】
...
⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên):
   • Máy Mxxx: UploadHook: 2026-10-22 06:44:35,695 [ERROR] scripts.tiktok_workflow.state_machine: Post verification inconclusive/failed: TIMEOUT
```

## 2. Phân Tích Nguyên Nhân Gốc (Root Cause Analysis)
- Quy trình upload video (`scripts.tiktok_workflow.state_machine`) thực hiện hậu kiểm bài đăng qua `PostVerifier.verify_post()`.
- Khi mạng hoặc TikTok duyệt video chậm quá 120s, script ghi nhận:
  `Post verification inconclusive/failed: TIMEOUT`
  và chuyển sang `_recheck_ambiguous_post()`. Khi không thể xác nhận 100% video đã hiển thị, script chọn dừng an toàn (fail-closed) để không spam đăng trùng lặp, sau đó dọn dẹp và đưa máy về màn hình Home (`LauncherActivity`).
- Tuy nhiên, trong `automation_core/batch_aggregator.py`, danh sách `CHALLENGE_KEYWORDS` có chứa từ khóa `"verification"`.
- Do bộ lọc chỉ quét chuỗi con (`in`), `"verification"` trong chuỗi lỗi đã bị xếp nhầm thành lỗi Captcha / Thử thách danh tính (`challenge_failure`).

## 3. Quy Trình Kiểm Chứng Hiện Trường O(1)
1. Chạy inspect O(1) kiểm tra trạng thái các máy bị cảnh báo:
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. Xác nhận 3 điều kiện:
   - Focus hiện tại là `LauncherActivity` (Home screen) hoặc TikTok đã đóng sạch.
   - Trạng thái màn hình là `OFF (Sleep/Dozing)` hoặc nghỉ an toàn.
   - Proxy kết nối tốt và trả về IP public bình thường.
3. **Kết luận**: **BÁO ĐỘNG GIẢ (FALSE POSITIVE)** — hoàn toàn không có Captcha hay mất phiên.

## 4. Kỷ Luật Phản Hồi Operator (Bottom-line First)
- **Trả lời trực diện ngay câu đầu tiên:** Khẳng định ngay là BÁO ĐỘNG GIẢ do watchdog bắt nhầm từ khóa, tài khoản và máy móc an toàn 100%. CẤM tuôn một tràng số liệu kỹ thuật (pin, nhiệt độ, IP) trước khi trả lời câu hỏi "Lỗi gì".
- **Hành động ngay lập tức:** Khi Operator yêu cầu fix, không chần chừ hay giải thích lan man, tiến hành sửa code O(1) ngay.

## 5. Quy Chuẩn Kiến Trúc Sửa Code & Closeout Gate
- **CẤM sửa theo kiểu thêm thô vào exclusion blacklist:**
  Việc nhét `"post verification"` vào `CHALLENGE_EXCLUSIONS` tạo ra bẫy adversarial (nếu chuỗi lỗi thực tế là `"post verification: captcha required"`, toàn bộ thông báo sẽ bị nuốt chửng).
- **Quy chuẩn Prefix-Stripping:**
  Định nghĩa `_CHALLENGE_STRIP_PREFIXES` và dùng `_strip_challenge_prefixes(text)` để gọt bỏ các tiền tố không phải challenge (`"profile verification"`, `"post verification"`) trước khi đối soát từ khóa (`CHALLENGE_KEYWORDS`).
- **3 Lớp Test Bắt Buộc (Negative & Adversarial):**
  1. Test triệt tiêu báo động giả: `UploadHook: Post verification inconclusive/failed: TIMEOUT` -> 0 challenge.
  2. Test không bỏ sót challenge thật: `Verification challenge required: please complete the CAPTCHA` -> 1 challenge.
  3. Test kịch bản lai (Adversarial): `post verification inconclusive: captcha required` -> 1 challenge.
  4. Test telemetry logging: kiểm tra `[CHALLENGE_EXCLUSION]` emit đúng log.
- **Quy trình Closeout Remediation:**
  `closeout_gate.py` (Sonnet) -> nếu `REJECTED`, dùng `sol_repair.py` (Sol High) làm First Responder đề xuất patch O(1) -> áp dụng và chạy focused test -> rerun `closeout_gate.py`.
