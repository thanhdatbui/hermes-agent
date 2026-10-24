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

## 1. Nguyên Tắc Cốt Lõi (Invariants)
1. **CẤM gửi ảnh mù / đối phó:** Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào, bắt buộc phải mở ảnh ra soi mắt kiểm tra trước.
2. **CẤM hạ cấp bằng chứng sang OCR text thô:** Text OCR chỉ dùng để hỗ trợ tọa độ/phân loại sơ bộ, KHÔNG thay thế được Vision để chứng minh giao diện. Khi tool Vision chết (503/Quota 429), CẤM dùng OCR text để báo cáo hoàn thành.
3. **Fail-Closed khi Vision Tool gặp sự cố:** Nếu `browser_vision` hoặc `ag_cli.py` bị lỗi 503 / 429, bước hiện tại BẮT BUỘC giữ trạng thái `UNVERIFIED / BLOCKED_VISION_UNAVAILABLE`.

## 2. Thang Leo Thang Vision Dự Phòng (Fallback Ladder)
1. **Kênh 1 (Claude Worker Reviewer):** Chạy `python D:/Taadaa/tools/claude_worker.py --role reviewer --timeout 300 "<prompt kiểm tra ảnh>"`. Claude CLI chạy bằng Anthropic API độc lập, có native vision đọc ảnh trực tiếp.
2. **Kênh 2 (Direct 9Router `:20128`):** Gọi endpoint `:20128` trực tiếp với model vision cụ thể (gpt-4o, claude-3-5-sonnet).
3. **Kênh 3 (User Clarify):** Nếu toàn bộ kênh vision đều chết, báo cáo sự cố hạ tầng trung thực, giữ `UNVERIFIED`, xin ý kiến User trước khi gửi ảnh thô (mặc định là KHÔNG gửi).
