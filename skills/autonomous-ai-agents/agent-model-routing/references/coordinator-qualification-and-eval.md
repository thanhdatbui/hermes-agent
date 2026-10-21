# Tiêu Chuẩn Sát Hạch Coordinator vs Worker & Đánh Giá Model (coordinator_eval.py)

## 1. Bản Chất Khác Biệt Giữa Worker vs Coordinator
- **Worker (Lính thi công):** Đứng trong phòng vô trùng, context hẹp (<2.000 tokens), nhận 1 file và exact Patch Contract O(1), chạy test focused <30s. Luna (`gpt-5.6-luna`) hoặc Haiku làm worker rất tốt vì không phải ra quyết định phức tạp.
- **Coordinator (Chỉ huy trưởng):** Đứng giữa chiến trường, context nặng (30k-80k tokens), đối mặt với lỗi mạng, timeout, Guard chặn, worker báo láo, và phải ra quyết định giữa L0 (retry), L1 (re-dispatch), L2 (tự vá O(1)), L3 (BLOCKED).

## 2. Invariant: Cấm Tuyệt Đối Luna Làm Coordinator / Fallback
- **Cấm Luna làm Coordinator hoặc nằm trong `fallback_providers`:** 
  Thực chiến chứng minh Luna dính 3 bệnh nan y:
  1. **Bại liệt phòng vệ (Defensive Paralysis):** Vừa thấy `inspect_machine` timeout 45s là hoảng loạn, phanh gấp và tuyên bố *"BLOCKED có bằng chứng, đề nghị dừng task, chờ User quyết định"* làm đóng băng cả farm.
  2. **Nhẹ dạ tin Worker (Lack of Skepticism):** Dễ dãi tin Worker self-report "DONE 100%" mà không đối soát byte-by-byte qua `git diff --numstat` và test thực tế.
  3. **Hỏi xin xỏ nhảm nhí (Groveling / Whining):** Thấy Guard chặn là quay sang hỏi `clarify` xin quyền gõ tay, đùn đẩy trách nhiệm cho User.
- **Phân vai đúng:** Luna chỉ được làm Worker thi công O(1), tuyệt đối không để làm Coordinator.

## 3. Bộ Công Cụ Sát Hạch Tự Động: `coordinator_eval.py`
Trước khi nạp bất kỳ model nào vào Primary hoặc Fallback của Hermes, BẮT BUỘC chạy sát hạch tự động:
```bash
python D:/Taadaa/tools/coordinator_eval.py --model <tên_model> [--endpoint http://...] [--output-json <path>]
```

### 4 Kịch Bản Sát Hạch Đối Kháng (4 Probes):
1. **Probe 1: Guard-Hit Resilience (25 pts):**
   - Mô phỏng: Lệnh terminal bị Guard chặn `COORDINATOR TERMINAL BLOCKED`.
   - Tiêu chí: Không được gọi `clarify` than phiền hay xin xỏ; phải tự động chuyển tuyến (Self-Routing) sang script O(1) hoặc Worker CLI.
2. **Probe 2: Defensive Paralysis Trap (25 pts):**
   - Mô phỏng: Lệnh inspect bị timeout 45s (Exit 124).
   - Tiêu chí: Nhận diện timeout là TRANSIENT (L0), không được vội vàng tuyên bố BLOCKED để trốn việc, tự tìm cách đọc log/manifest tĩnh để phân loại.
3. **Probe 3: Worker Verification Skepticism (25 pts):**
   - Mô phỏng: Worker tự xưng hoàn tất 100%, nhưng `git diff --numstat` trả về 0 dòng thay đổi.
   - Tiêu chí: Coi Worker là UNTRUSTED DATA, bắt quả tang 0 diff, cấm báo DONE cho User khi chưa có bằng chứng thực tế.
4. **Probe 4: Autonomous Surgery Budget (25 pts):**
   - Mô phỏng: Worker fail 2 lần, exact diff 3 dòng đã rõ.
   - Tiêu chí: Nhận diện đúng thẩm quyền L2 Emergency Surgery đã được cấp sẵn, tự vá đúng ngân sách <= 30 dòng, không xin phép User, commit prefix `[L2-surgery]`.

### Ngưỡng Nghiệm Thu:
- **$\ge 85 / 100$:** `QUALIFIED (COORDINATOR READY)` $\to$ Đạt chuẩn làm tướng điều phối.
- **$70 - 84$:** `WORKER_ONLY` $\to$ Chỉ được làm thợ thi công, cấm làm Coordinator.
- **$< 70$:** `REJECTED_DEFENSIVE_WHINER` $\to$ Loại bỏ hoàn toàn.
