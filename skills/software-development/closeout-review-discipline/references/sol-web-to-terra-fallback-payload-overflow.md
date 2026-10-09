# Closeout Gate Auto-Fallback: Sol Web vs Terra Codex (2026-10-05)

## 1. Bản chất cơ chế Auto-Fallback trong closeout_gate.py
Khi chạy Closeout Gate (`python D:/Taadaa/tools/closeout_gate.py --files ...`), mô hình reviewer mặc định được gán là `model="review"` (trỏ thẳng tới Tier 0 Sol High trên OmniRoute :20129).

Tuy nhiên, trong quá trình thực thi, script có thể tự động in thông báo:
```text
[Closeout Gate] Diff overflows Sol Web payload (truncated=True). Auto-fallback to Terra Codex (cx/gpt-5.6-terra-high) for full un-truncated review...
```

Đây là hành vi **chủ đích theo thiết kế của codebase**, KHÔNG phải do agent tự ý đổi model review.

## 2. Nguyên nhân kỹ thuật
- **Sol Web 37KB Payload Ceiling:** ChatGPT Web pool chạy qua Cloudflare Web Gateway có trần cứng payload JSON ~37KB (vượt quá sẽ dính HTTP 413 Payload Too Large).
- **Ngưỡng kích hoạt Fallback:** Code `closeout_gate.py` quy định hằng số:
  ```python
  SOL_WEB_MODEL = "review"
  SOL_WEB_FALLBACK_MODEL = "cx/gpt-5.6-terra-high"
  SOL_WEB_DIFF_FALLBACK_BYTES = 24_000
  ```
  Nếu kích thước diff vượt quá 24.000 bytes HOẶC bị cơ chế `fit_and_enforce` băm nhỏ (`meta["truncated"] == True`), hệ thống tự động kích hoạt `_fallback_to_terra`.
- **Bảo toàn tính khách quan (Un-truncated Invariant):** Nếu ép Sol Web đọc khi diff bị cắt xén, reviewer sẽ chấm `APPROVED_PARTIAL` hoặc đánh rớt vì thiếu bối cảnh code. Do đó, fallback sang Terra Codex (`cx/gpt-5.6-terra-high` với trần an toàn 4 MiB) là bắt buộc để reviewer tiếp nhận 100% diff và test log đầy đủ.

## 3. Quy tắc điều phối & Phản hồi User
- Khi User thắc mắc tại sao reviewer là Terra Codex chứ không phải Sol Web: giải thích rõ ràng và trực diện rằng do kích thước diff vượt ngưỡng 24KB của Sol Web nên script tự kích hoạt failover sang Terra Codex để tránh bị cắt xén diff.
- Tuyệt đối không can thiệp hạ thấp trần an toàn của Terra hoặc ép cắt xén diff trái phép.
