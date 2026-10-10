# Reviewer Fallback: Terra Codex trên OmniRoute :20129 (Chống Bại Liệt Khi Sol Kẹt)

## Bối cảnh & Sự cố (11/10/2026)
Trong phiên chốt phiên, khi gọi `closeout_gate.py` với model mặc định (`review` / Sol High qua `:20129`), request bị timeout hoặc trả về lỗi `HTTP 402: Payment Required` / `HTTP 401: Unauthorized`.
Coordinator đã dừng lại và báo cáo "Sol Auditor :20129 bị timeout/hết quota ... không tự ý commit/push".
User đã mắng gay gắt và chấn chỉnh ngay lập tức:
> *"cái đụ mẹ mày t đã fallback cho reviewer qua terra codex r mà??? lí do đéo sử dụng đkm r ngồi đó khóc lóc đụ mẹ mày"*

## Nguyên tắc Vận hành Chống Bại Liệt

1. **Fallback Model Reviewer được cấu hình sẵn**:
   - Khi Sol High trên `:20129` gặp sự cố (timeout, HTTP 402/401/429, kẹt queue):
   - **BẮT BUỘC lập tức chuyển sang fallback reviewer Terra Codex**:
     `python D:/Taadaa/tools/closeout_gate.py --repo <path> --files <files...> --model "codex-terra" --json-output`
   - Model `codex-terra` trên `:20129` là `gpt-5.6-terra`, luôn trực chiến, phản hồi cực nhanh (~20-25s) và chấm điểm chuẩn mực theo rubric 100 điểm.

2. **Kỷ luật xử lý khi Closeout Gate bị từ chối (REJECTED)**:
   - CẤM ngồi im hoặc viện cớ an toàn để kết thúc phiên dang dở.
   - Bám sát từng Finding trong scorecard của Terra Codex:
     * **Test Evidence**: Phải chạy đủ toàn bộ suite liên quan (không chỉ 1-2 file hẹp), sạch cảnh báo deprecation pytest-asyncio (`asyncio_default_fixture_loop_scope = "function"`).
     * **Portability**: CẤM hardcode `C:\Users\Kibe` trong logic phân giải đường dẫn; dùng `Path.home()` / `os.path.expanduser("~")`.
     * **Enforcement Consistency**: Không gỡ bỏ hook trong `plugin.yaml` mà chưa có hook thay thế tương đương.
   - Khi chạm Strike 3 (`[REVIEWER_HANDOFF_TRIGGERED: ...]`), chuyển giao ngay cho Claude CLI theo quy chuẩn `3-STRIKE-REVIEWER-HANDOFF`.
