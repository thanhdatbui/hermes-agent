# Kiến Trúc Tự Động Dọn Rác Bộ Nhớ (Two-Stage Memory Garbage Collection & Watchdog)

## 1. Nguồn Gốc & Sự Cố Thực Tế (2026-10-25)
- **Vấn đề bùng nổ Token:** Qua rà soát log thực tế trên OmniRoute, System Prompt và Memory phình to khiến mỗi turn chat phải cõng 17.000–19.000 tokens overhead trước khi tính đến lịch sử hội thoại.
- **Thất bại của giải pháp cấm đoán cực đoan:** Ban đầu, Coordinator áp dụng điều khoản cấm tuyệt đối AI tự động lưu memory (`CẤM TỰ ĐỘNG LƯU MEMORY / save proactively`). Điều này lập tức bị User phản bác:
  > *"Hay vẫn để nó lưu rồi định kỳ đi dọn. Chứ tao phải ra lệnh lưu phiền lắm. Mà không tự động lưu mất mẹ sức mạnh của Hermes Agent."*
- **Bài học cốt lõi:** Bắt User phải tự gõ lệnh nhớ vừa gây phiền toái, vừa triệt tiêu năng lực tự thích ứng và học hỏi chủ động (*continuous learning*) của Hermes. Giải pháp chuẩn là **cho phép lưu chủ động + cơ chế tự dọn rác định kỳ (Garbage Collection)**.

---

## 2. Kiến Trúc Dọn Rác 2 Giai Đoạn (Two-Stage GC Policy)

```
[Mỗi turn chat bình thường]
   └── Hermes tự do học và lưu chủ động: Persona, Vibe, Feedback, Quirk mới.

[Cron Job 6 tiếng/lần: hermes-memory-garbage-collector]
   ├── STAGE 1: Dọn dẹp liên tục (Continuous Sanitization)
   │     ├── Khử trùng lặp (Deduplication): Tính SHA-256 hash trên chuỗi chuẩn hóa khoảng trắng.
   │     └── Gọt quy tắc đã cơ giới hóa (Mechanized Rules): Tự động xóa các mục đã có script/hook
   │         (streak follow, exit 126, worker floor 300s, shift pool, reboot game guard...).
   │
   └── STAGE 2: Siết ngân sách (Over-Capacity Budget Clamp)
         ├── Kích hoạt khi tổng ký tự sau Stage 1 > 70% trần (MEMORY > 1.540 chars, USER > 962 chars).
         ├── Tỉa bớt các entry không thuộc diện bảo vệ cho tới khi dung lượng <= 70%.
         └── BẢO TỒN NGUYÊN VẸN CÁC MỤC BẢO VỆ (Protected Persona):
             * Vibe O(1), ghét lấp liếm/đùn việc.
             * Advisor Claude 100% On-Demand.
             * Hand-off đủ thông tin.
             * Auto-heal ngầm gửi ảnh MEDIA.
             * Cơ chế học hỏi chủ động & Dynamic Skill.
```

---

## 3. Các Nguyên Tắc Kỹ Thuật Đã Được Thẩm Định (Closeout Gate 94/100)

1. **Khử trùng lặp bằng Full-Text Hash:** Tuyệt đối không dùng tiền tố ngắn (ví dụ 50 ký tự đầu) làm fingerprint vì dễ gây va chạm giả (false-positive collision), xóa nhầm 2 entry có cùng mở đầu nhưng nội dung khác nhau. Dùng SHA-256 toàn bộ entry đã chuẩn hóa.
2. **Siết cứng giới hạn dung lượng:** Khi kiểm tra thêm entry trong Stage 2, phải đánh giá độ dài dự kiến sau khi thêm `len(format_entries(surplus_kept + [e])) <= threshold` trước khi quyết định giữ lại, đảm bảo kết quả không bao giờ vượt ngưỡng 70%.
3. **Cảnh báo tràn bộ nhớ bảo vệ (`PROTECTED_OVERFLOW`):** Nếu các entry được bảo vệ tự thân chúng vượt quá trần tối đa (`max_chars`), script ghi nhận cảnh báo `[WARNING]`, đổi trạng thái sang `PROTECTED_OVERFLOW` và báo động ra `stderr`.
4. **Giao dịch ghi nguyên tử & Rollback xuyên thư mục:**
   - Script cập nhật đồng thời cả thư mục runtime (`$LOCALAPPDATA/hermes/memories/`) và thư mục Git backup (`D:/Taadaa/Hermes/deploy/hermes-home/memories/`).
   - Trước khi ghi, sao lưu nội dung cũ vào bộ nhớ. Nếu bất kỳ lượt ghi nào thất bại, lập tức rollback toàn bộ các file đã ghi về trạng thái ban đầu.
5. **Chuẩn Silent Watchdog (Fail-Closed):**
   - Khi bộ nhớ sạch sẽ (<70% và không có rác): Thoát 0 với stdout rỗng 100% (không tốn token, không bắn tin nhắn rác vào Telegram).
   - Khi có thao tác gọt rác: Xuất telemetry chi tiết về dung lượng trước/sau và danh sách mục đã tỉa.
   - Khi gặp lỗi file (`READ_ERROR`, `WRITE_ERROR`, `FILE_NOT_FOUND`): In lỗi ra `stderr` và thoát mã `exit(1)` ngay lập tức, tuyệt đối không được exit 0 âm thầm.

---

## 4. Tích Hợp Vận Hành Cron Job

- **Script Canonical:** `D:/Taadaa/tools/auto_prune_memory.py` (đã đồng bộ vào `%LOCALAPPDATA%/hermes/scripts/auto_prune_memory.py`).
- **Test Suite:** `D:/Taadaa/tools/tests/test_auto_prune_memory.py` (14/14 tests PASSED 100%).
- **Lệnh Cronjob:**
  ```python
  cronjob(
      action="create",
      name="hermes-memory-garbage-collector",
      schedule="0 */6 * * *",
      script="auto_prune_memory.py",
      workdir="D:/Taadaa/tools",
      no_agent=True,
      deliver="origin"
  )
  ```
- **Chạy kiểm thử thủ công:**
  ```bash
  python D:/Taadaa/tools/auto_prune_memory.py --verbose
  ```
