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
- Do thiếu `"post verification"` trong `CHALLENGE_EXCLUSIONS`, `batch_aggregator` đã quét trúng từ `"verification"` trong chuỗi lỗi và xếp nhầm thành lỗi Captcha / Thử thách danh tính (`challenge_failure`).

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

## 5. Phương Án Xử Lý & Worker Dispatch
- **Bổ sung loại trừ:** Thêm `"post verification"` vào `CHALLENGE_EXCLUSIONS` trong `src/automation_core/batch_aggregator.py`.
- **Thêm unit test:** Thêm test case vào `tests/test_batch_aggregator.py` kiểm chứng `MachineResult` với chuỗi lỗi `UploadHook: Post verification inconclusive/failed: TIMEOUT` có `challenge_count == 0` và `should_alert is False`.
- **Dispatch Worker qua Single Dispatch Gateway:**
  ```bash
  python D:/Taadaa/tools/dispatch_worker.py --workdir "D:/Taadaa/automation-core" --timeout 180 "<Patch Contract O(1)>"
  ```
- **Lưu ý Fallback:** Nếu Agy CLI gặp sự cố model config, Single Dispatch Gateway sẽ tự động failover sang Haiku Tier-2 trong vòng < 30s.
