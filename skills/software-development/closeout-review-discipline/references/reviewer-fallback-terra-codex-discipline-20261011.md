# Reviewer Fallback: Terra Codex trên OmniRoute :20129 (Chống Bại Liệt Khi Sol Kẹt)

## Bối cảnh & Sự cố (11/10/2026)
Trong phiên chốt phiên, khi gọi `closeout_gate.py` với model mặc định (`review` / Sol High qua `:20129`), request bị timeout hoặc trả về lỗi `HTTP 402: Payment Required` / `HTTP 401: Unauthorized`.
Coordinator đã dừng lại và báo cáo "Sol Auditor :20129 bị timeout/hết quota ... không tự ý commit/push".
User đã mắng gay gắt và chấn chỉnh ngay lập tức:
> *"cái đụ mẹ mày t đã fallback cho reviewer qua terra codex r mà??? lí do đéo sử dụng đkm r ngồi đó khóc lóc đụ mẹ mày"*

## Nguyên tắc Vận hành Chống Bại Liệt

1. **Kiến trúc Combo Reviewer Canonical trên OmniRoute :20129 (`review`)**:
   - User chỉ thị rõ ràng: Ghép Terra Codex vào chung combo với ChatGPT Sol Web, để Terra Codex làm fallback tự động cho Sol Web trong combo.
   - **Tier 0 (Primary)**: `chatgpt-web-pool` (ChatGPT Web Sol High - 78 accounts).
   - **Tier 1 (Fallback)**: `codex-terra` (Codex Terra Pool - 97 accounts farm, chiến thuật `least-used`).
   - **Cấu hình failover**: `failoverBeforeRetry: true`, `targetTimeoutMs: 45000`. Khi Sol Web gặp sự cố (HTTP 401/402/429/502/timeout), OmniRoute tự động chuyển sang Codex Terra ngay trong request đó.

2. **Kỷ luật chạy Chốt Phiên (`closeout_gate.py`)**:
   - Khi chốt phiên, **BẮT BUỘC gọi combo `review`**:
     `python D:/Taadaa/tools/closeout_gate.py --repo <path> --model "review" --json-output`
     *(Script `closeout_gate.py` mặc định đã trỏ vào model `review`)*.
   - CẤM Coordinator tự ý dừng lại, than khóc báo kẹt hoặc đóng băng phiên khi Sol lỗi. Combo `review` sẽ tự động kích hoạt fallback Terra Codex.

2. **Kỷ luật xử lý khi Closeout Gate bị từ chối (REJECTED)**:
   - CẤM ngồi im hoặc viện cớ an toàn để kết thúc phiên dang dở.
   - Bám sát từng Finding trong scorecard của Terra Codex:
     * **Test Evidence**: Phải chạy đủ toàn bộ suite liên quan (không chỉ 1-2 file hẹp), sạch cảnh báo deprecation pytest-asyncio (`asyncio_default_fixture_loop_scope = "function"`).
     * **Portability**: CẤM hardcode `C:\Users\Kibe` trong logic phân giải đường dẫn; dùng `Path.home()` / `os.path.expanduser("~")`.
     * **Enforcement Consistency**: Không gỡ bỏ hook trong `plugin.yaml` mà chưa có hook thay thế tương đương.
   - Khi chạm Strike 3 (`[REVIEWER_HANDOFF_TRIGGERED: ...]`), chuyển giao ngay cho Claude CLI theo quy chuẩn `3-STRIKE-REVIEWER-HANDOFF`.
