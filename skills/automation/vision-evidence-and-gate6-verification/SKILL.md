---
name: vision-evidence-and-gate6-verification
description: "Use when vision 503 fails Gate 6. Fallback Claude CLI."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [gate6, vision, visual-evidence, ocr, claude-worker, fail-closed]
---

# Vision Evidence & Gate 6 Verification SOP

Tài liệu quy trình chuẩn khi thực thi Invariant Soi Mắt & Gate 6 Visual Evidence trên Taadaa Farm.

- Chi tiết SOP đầy đủ: [`references/vision-down-fail-closed-and-claude-cli-fallback-sop.md`](references/vision-down-fail-closed-and-claude-cli-fallback-sop.md)
- Đăng ký Receipt Media Gate & xử lý chặn clarify: [`references/media-gate-receipt-registration-and-clarify-lockout.md`](references/media-gate-receipt-registration-and-clarify-lockout.md)
- Phân bậc Receipt T0/T1/T2/T3 & chống bẫy im lặng Gate 6: [`references/tiered-verifier-and-gate6-incentive-alignment.md`](references/tiered-verifier-and-gate6-incentive-alignment.md)
- Gate cơ học có chỉ dẫn (Action-Forcing Guidance) & Invariant Tiếng Việt có dấu: [`references/vietnamese-diacritics-profile-and-action-forcing-guidance-gates.md`](references/vietnamese-diacritics-profile-and-action-forcing-guidance-gates.md)
- Chống Chụp Mù Launcher & Cuộn Lưới Video Below-the-fold: [`references/pre-capture-focus-guard-and-anti-launcher-hallucination.md`](references/pre-capture-focus-guard-and-anti-launcher-hallucination.md)
- Điều Tra Sự Cố Bị Vượt Mặt Media Gate & Cơ Chế Chặn Ký Receipt Rỗng: [`references/media-gate-bypass-investigation-and-grounding-fix.md`](references/media-gate-bypass-investigation-and-grounding-fix.md)
- SOP Thẩm Định Thị Giác Đa Tầng Cơ Học (Sol -> Agy -> Claude): [`references/tiered-vision-fallback-mechanical-sop.md`](references/tiered-vision-fallback-mechanical-sop.md)

## 1. Nguyên Tắc Cốt Lõi (Invariants)
1. **CẤM gửi ảnh mù / đối phó:** Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào, bắt buộc phải mở ảnh ra soi mắt kiểm tra trước.
2. **CẤM hạ cấp bằng chứng sang OCR text thô:** Text OCR chỉ dùng để hỗ trợ tọa độ/phân loại sơ bộ, KHÔNG thay thế được Vision để chứng minh giao diện. Khi tool Vision chết (503/Quota 429), CẤM dùng OCR text để báo cáo hoàn thành.
3. **Quy Trình Phân Bậc Receipt Khi Vision 503 (Tiered Verifier SOP):**
   - **T0 (Primary Vision):** `browser_vision` thành công. Đăng ký receipt và gửi `MEDIA:`.
   - **T1 (Fallback Vision):** Gọi Claude CLI reviewer / 9router direct để soi ảnh độc lập.
   - **T2 (Cơ học - Mechanical Receipt):** Khi toàn bộ LLM Vision chết, cho phép sinh receipt T2 dựa trên `uiautomator dump` (thuộc tính text) + WinRT OCR đối soát theo contract O(1). Gửi `MEDIA:` kèm nhãn rõ: `[T2 - Cơ học, Vision 503]`.
   - **T3 (Không có Verifier):** DỪNG THAO TÁC TIẾP THEO. Gửi ảnh gắn nhãn `[CHƯA SOI - CHỜ USER XÁC NHẬN]`. CẤM TUYỆT ĐỐI im lặng bỏ gửi ảnh để chạy tiếp (Max blind steps = 1 là bất biến; im lặng nặng tội hơn gửi ảnh có cảnh báo).
4. **Cơ chế Hook HMAC-SHA256 Media Gate (`guard_media_vision_gate.py`):** Mọi ảnh `MEDIA:<path>` gửi qua Telegram bắt buộc phải có receipt hợp lệ (TTL <= 300s, ký bằng sha256 và mtime). Đăng ký receipt bằng lệnh `python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<path>" --tool winrt_ocr --ocr "<tokens>"` trước khi xuất thẻ `MEDIA:`. CẤM TUYỆT ĐỐI đăng ký receipt rỗng (thiếu `--ocr`) để lách cơ chế phát hiện mâu thuẫn của Gate; receipt rỗng sẽ khiến Gate fail-open và cấp chứng chỉ giả cho thông tin sai sự thật. Bắt buộc có token OCR thật hoặc dùng `vision_fallback_reader.py` để sinh receipt chuẩn. Khi Hand-off Lock Active (`handoff_lock_active.json`), công cụ `clarify` bị chặn tự động — Coordinator phải trình bày các phương án đề xuất trực tiếp trên chat thay vì gọi `clarify`.
5. **Pre-Capture Focus & Anti-Launcher Semantic Gate:** Trước khi screencap, BẮT BUỘC kiểm tra focus máy (`inspect_machine.py <N>`); nếu đang ở Launcher/Splash, phải khôi phục app vào foreground và điều hướng đúng tab. Sau khi pull ảnh về, BẮT BUỘC chạy WinRT OCR đối soát: nếu ảnh chứa từ khóa Launcher (Chrome, Photos, Cài đặt, Laban Key...) hoặc Splash đen $\rightarrow$ FAIL-CLOSED, CẤM ký receipt và CẤM gửi thẻ `MEDIA:`. CẤM TUYỆT ĐỐI ảo giác nhìn thấy nội dung khi ảnh thực tế là Launcher.
6. **Tiêu chuẩn nghiệm thu Ghim bài (Pin Top) & Micro-swipe Giữ Định Danh:**
   - **CẤM suy diễn Pin từ View cao:** Video nằm ở ô 1 có view cao (ví dụ 33K) KHÔNG CÓ NGHĨA là đã ghim (có thể chỉ là video mới nhất). Chỉ công nhận đã ghim khi TẬN MẮT THẤY huy hiệu chữ đỏ `Đã ghim` (Pinned badge) ở góc trên bên trái thumbnail. CẤM BỊA ĐẶT nhãn đỏ khi ảnh không có.
   - **Micro-swipe giữ trọn khung định danh:** Khi cuộn kéo lưới video lên, CẤM vuốt quá đà làm bay mất avatar, username `@...` và bio. Sử dụng micro-swipe nhẹ (`input swipe 540 1100 540 850 300`), đảm bảo 1 bức ảnh chụp trọn vẹn cả định danh tài khoản lẫn hàng 1 của lưới video có nhãn "Đã ghim".

## 2. Thang Leo Thang Vision Dự Phòng (Fallback Ladder)
Thứ tự fallback đọc ảnh chuẩn hoá 100% đồng bộ với kiến trúc Worker Dispatch:
- **Tier 0 (Primary - Coordinator):** Mặc định Coordinator tự soi mắt bằng `browser_vision` / native vision trong phiên.
- **Tier 1 (Fallback 1): Sol Web Vision** (`:20129` qua OmniRoute) — 100% Free, endpoint `auto/best-vision` (qua `_ask_sol_web_vision`).
- **Tier 2 (Fallback 2): Agy CLI Vision** (`agy vision` / `ag_cli.py ask` qua pool 29 tài khoản Google One Pro).
- **Tier 3 (Fallback 3): Claude Worker CLI** (`claude_worker.py --role reviewer`).
- **Công cụ cơ học chuẩn:** Sử dụng trực tiếp `python D:/Taadaa/tools/vision_fallback_reader.py --image "<path>" --question "<nội dung>" --mode auto_fallback`. Script tự động điều phối qua Sol Web -> Agy CLI -> Claude Worker, tự động ký HMAC receipt vào `vision_receipts.jsonl`.
- **Fail-Closed:** Nếu cả 3 tier fallback đều thất bại (503, timeout, cạn quota): CẤM gửi ảnh mù, CẤM hạ cấp sang OCR text thô để báo cáo, bắt buộc giữ trạng thái `UNVERIFIED / BLOCKED_VISION_UNAVAILABLE`. CẤM lưu memory thủ công khi đã có tầng cơ học đảm nhiệm.
