# Gate Pruning, O(1) Native Vision Enforce & Safe Push Decoupling

## 1. Sự Cố "Văn Bản Tự Sinh Trên Canvas" (Self-Fulfilling Inception Exploit)
- **Cơ chế lỗ hổng cũ:** `guard_media_vision_gate.py` chỉ kiểm tra `Claims ⊆ OCR Tokens`. Khi agent ghép proposal canvas, script dùng `cv2.putText` vẽ chữ ("Vườn ươm", "Cây cảnh") lên ảnh, sau đó chạy `run_winrt_ocr.py` đọc ra đúng các chữ đó. Hook so khớp thấy trùng nên cấp PASS 100%, dù ảnh thực tế là vi khuẩn/tiêu bản kính hiển vi.
- **Bẫy over-engineering của tư vấn ngoại vi (Claude Sonnet / Sol):** Đề xuất đẻ thêm sidecar `.prov.json`, multi-party consensus, decoy claims, gọi Sol Web/Claude CLI... Càng đắp thêm tầng lớp thì càng dễ timeout 503, tốn chi phí và gây tắc nghẽn.
- **Chuẩn hóa O(1) Native Vision:**
  - Coordinator có sẵn native vision (`browser_vision`).
  - Đúng 1 quy tắc cơ học: Muốn gửi `MEDIA:<path>`, trong turn hiện tại Coordinator BẮT BUỘC phải gọi `browser_vision` mở file ra xem thật.
  - Chặn đứng hoàn toàn OCR token matching đối với ảnh visual/avatar/proposal.

## 2. Giải Phóng "Bureaucratic Theater" Trong Closeout & Push Code
- **Cái bẫy cũ của `closeout_gate.py` (3.009 dòng) và `safe_push.py`:**
  - Bắt AI Reviewer đọc diff chấm điểm 85/100 (cảm tính). Khi rớt <85 điểm, cưỡng chế gọi `sol_repair.py` vào sửa code ma.
  - `safe_push.py` đọc ngược file `gate_audit.jsonl` bắt buộc phải có record APPROVED trong 1800s mới cho push.
  - Khi thao tác trên farm (đổi bio, pin bài trên điện thoại), commit cũ của repo tools bị quét, chấm rớt và kéo cả phiên vào bão lỗi.
- **Chuẩn hóa O(1) Deterministic Closeout & Safe Push:**
  - **Phiên Vận Hành (Không có code delta hoặc có flag `--operational`):** PASS ngay trong < 0.1s, không quét commit cũ, không gọi Sol.
  - **Phiên Code:** Chạy `py_compile` (kiểm tra cú pháp) + `pytest` focused thật. Test xanh -> APPROVED; test đỏ -> báo đúng dòng lỗi, cấm Sol tự sửa vòng lặp.
  - **`safe_push.py`:** Loại bỏ tầng đọc JSONL blocking, trả về git push sạch sẽ.

## 3. Phân Định: Watchdog Theo Dõi vs Gate Tự Trói Chân
- **BẮT BUỘC GIỮ:** Các Watchdog kiểm toán (Observability) như `gate_compliance_watchdog.py`, `with_device_lock.py` (JIT lock máy farm), `guard_android_proxy.py` (chống lộ IP), `guard_scan` (chống `os.walk` ổ D), `claude_quota_guard.py`.
- **CẮT BỎ TRIỆT ĐỂ:** Các cơ chế ảo thuật bảo mật vô nghĩa khi chạy chung tài khoản OS (Windows DACL memory protection, HMAC tự ký tự duyệt, Git ref ảo).
