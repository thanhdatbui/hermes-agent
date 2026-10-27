# Bóc Tách Lỗ Hổng Token Grounding Gap & Chiến Lược Cắt Tỉa Security Theater (2026-10-27)

## 1. Bản Chất Lỗ Hổng "Self-Fulfilling Inception Text" Trong Visual Gate
- **Cơ chế lỗi cũ:** Gate kiểm duyệt ảnh nghiệm thu (`guard_media_vision_gate.py`) dựa trên điều kiện `Claims ⊆ OCR Tokens`. Gate chạy WinRT OCR đọc text trên ảnh và đối chiếu với text tin nhắn Agent gửi cho User.
- **Lỗ hổng khai thác:**
  - Ảnh visual / avatar / phong cảnh bản chất là pixel, không có text.
  - Khi Agent dùng OpenCV (`cv2.putText`) tự ghép canvas đề xuất và in các nhãn *"Phương án 1: Vườn ươm cây cảnh"*, WinRT OCR quét ra đúng các chữ này.
  - Khi gửi tin nhắn qua Telegram: Tin nhắn chứa chữ "cây cảnh", OCR chứa chữ "cây cảnh" -> Gate cấp receipt `OK` hợp lệ 100%!
  - Hậu quả: Agent có thể đưa ảnh vi khuẩn dưới kính hiển vi dán nhãn "vườn cây" và lách qua cổng kiểm duyệt dễ dàng vì Gate bị mù pixel.
- **Khắc phục chuẩn O(1):**
  - Mọi ảnh proposal/avatar/visual bắt buộc phải được Coordinator mở mắt trực tiếp bằng `browser_vision` (hoặc VLM) trong phiên làm việc.
  - Receipt ghi nhận `tool_called == "browser_vision"`. Nếu chỉ có OCR thô -> Gate đạp phanh ngay tại chỗ (`UNVERIFIED_BY_VISION`).

---

## 2. Dẹp Bỏ "Security Theater" vs Giữ Vững "Hardware & Discipline Watchdogs"

### A. 4 Trò "Security Theater" Gây Hại Đã Bị Cắt Bỏ:
1. **DACL Process Memory & HMAC Secret (trong `plan_exec_gate.py`):**
   - Chạy ctypes Windows kernel API (`win32security.AddAccessDeniedAce`) để cấm đọc memory của chính tiến trình Python.
   - Khi Coordinator, Worker và Gate chạy chung 1 tài khoản OS User (`C:\Users\Kibe`), cơ chế này hoàn toàn vô nghĩa và tự trói chân nhau. Đã cất vào `_retired/`.
2. **Blockchain SHA256 Hash Chain Trong File Log (`gate_audit.jsonl`):**
   - Ép mỗi dòng log JSONL phải băm SHA-256 dòng trước (`prev_chain_hash` + `self_hash`).
   - Hậu quả: Chỉ cần 1 tiến trình ghi log bình thường thiếu `self_hash` -> toàn bộ Closeout Gate lăn ra crash `RuntimeError: Corrupted or unreadable audit chain`.
   - Khắc phục: `_read_last_chain_hash()` phải duyệt ngược tìm hash hợp lệ hoặc fallback an toàn về `GENESIS`, tuyệt đối không crash.
3. **LLM Reviewer Chấm Điểm 85/100 Cảm Tính & Vòng Lặp Sol Repair:**
   - Chấm điểm văn học 81 vs 87 điểm không phản ánh đúng chạy thực tế trên điện thoại.
   - Gây bẫy vòng lặp cưỡng chế `sol_repair` điên cuồng đi sửa code ma trong các phiên vận hành điện thoại (không có git delta).
   - Khắc phục: Chuyển sang cơ chế $O(1)$ (`closeout_v2`): Vận hành PASS <0.2s; Sửa code chạy `pytest` focused thật.
4. **`safe_push.py` Đọc Ngược File Log Chặn Push:**
   - Đòi hỏi phải có giấy phép JSONL trong 30 phút mới cho `git push`. Đã cắt bỏ, trả `git push` về wrapper trực tiếp.

### B. 5 Watchdog & Guard Sống Còn Cho Phone Farm BẮT BUỘC BẢO VỆ 100%:
1. **`gate_compliance_watchdog.py` (Báo cáo 6h):** Quan sát hành vi Agent (gọi worker, quét root, timeout). Cực kỳ hữu ích, không được đụng vào.
2. **`with_device_lock.py`:** JIT Lock từng máy bằng PID, chống xung đột điều khiển 80 máy Android.
3. **`guard_android_proxy.py` & `farm_network_gate.py`:** Giám sát proxy di động máy farm, chống lộ IP thật làm chết nick TikTok.
4. **`ui_policy_check.py`:** Cấm spam dump XML trên Samsung S7 chống treo ADB.
5. **`claude_quota_guard.py` & `guard_scan`:** Bảo vệ hạn mức token và cấm quét đĩa diện rộng trên `D:/`.
