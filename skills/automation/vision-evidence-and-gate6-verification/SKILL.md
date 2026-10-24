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

## 1. Nguyên Tắc Cốt Lõi (Invariants)
1. **CẤM gửi ảnh mù / đối phó:** Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào, bắt buộc phải mở ảnh ra soi mắt kiểm tra trước.
2. **CẤM hạ cấp bằng chứng sang OCR text thô:** Text OCR chỉ dùng để hỗ trợ tọa độ/phân loại sơ bộ, KHÔNG thay thế được Vision để chứng minh giao diện. Khi tool Vision chết (503/Quota 429), CẤM dùng OCR text để báo cáo hoàn thành.
3. **Quy Trình Phân Bậc Receipt Khi Vision 503 (Tiered Verifier SOP):**
   - **T0 (Primary Vision):** `browser_vision` thành công. Đăng ký receipt và gửi `MEDIA:`.
   - **T1 (Fallback Vision):** Gọi Claude CLI reviewer / 9router direct để soi ảnh độc lập.
   - **T2 (Cơ học - Mechanical Receipt):** Khi toàn bộ LLM Vision chết, cho phép sinh receipt T2 dựa trên `uiautomator dump` (thuộc tính text) + WinRT OCR đối soát theo contract O(1). Gửi `MEDIA:` kèm nhãn rõ: `[T2 - Cơ học, Vision 503]`.
   - **T3 (Không có Verifier):** DỪNG THAO TÁC TIẾP THEO. Gửi ảnh gắn nhãn `[CHƯA SOI - CHỜ USER XÁC NHẬN]`. CẤM TUYỆT ĐỐI im lặng bỏ gửi ảnh để chạy tiếp (Max blind steps = 1 là bất biến; im lặng nặng tội hơn gửi ảnh có cảnh báo).
4. **Cơ chế Hook HMAC-SHA256 Media Gate (`guard_media_vision_gate.py`):** Mọi ảnh `MEDIA:<path>` gửi qua Telegram bắt buộc phải có receipt hợp lệ (TTL <= 300s, ký bằng sha256 và mtime). Đăng ký receipt bằng lệnh `python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<path>" --ocr "<tokens>"` trước khi xuất thẻ `MEDIA:`. Khi Hand-off Lock Active (`handoff_lock_active.json`), công cụ `clarify` bị chặn tự động — Coordinator phải trình bày các phương án đề xuất trực tiếp trên chat thay vì gọi `clarify`.
5. **Pre-Capture Focus & Anti-Launcher Semantic Gate:** Trước khi screencap, BẮT BUỘC kiểm tra focus máy (`inspect_machine.py <N>`); nếu đang ở Launcher/Splash, phải khôi phục app vào foreground và điều hướng đúng tab. Nếu nghiệm thu lưới video bài đăng (Pin Top), phải vuốt nhẹ (`input swipe 540 1300 540 700 300`) kéo nội dung below-the-fold lên màn hình. Sau khi pull ảnh về, BẮT BUỘC chạy WinRT OCR đối soát: nếu ảnh chứa từ khóa Launcher (Chrome, Photos, Cài đặt, Laban Key...) hoặc Splash đen $\rightarrow$ FAIL-CLOSED, CẤM ký receipt và CẤM gửi thẻ `MEDIA:`. CẤM TUYỆT ĐỐI ảo giác nhìn thấy nội dung khi ảnh thực tế là Launcher.

## 2. Thang Leo Thang Vision Dự Phòng (Fallback Ladder)
1. **Kênh 1 (Claude Worker Reviewer):** Chạy `python D:/Taadaa/tools/claude_worker.py --role reviewer --timeout 300 "<prompt kiểm tra ảnh>"`. Claude CLI chạy bằng Anthropic API độc lập, có native vision đọc ảnh trực tiếp.
2. **Kênh 2 (Direct 9Router `:20128`):** Gọi endpoint `:20128` trực tiếp với model vision cụ thể (gpt-4o, claude-3-5-sonnet).
3. **Kênh 3 (User Clarify):** Nếu toàn bộ kênh vision đều chết, báo cáo sự cố hạ tầng trung thực, giữ `UNVERIFIED`, xin ý kiến User trước khi gửi ảnh thô (mặc định là KHÔNG gửi).
