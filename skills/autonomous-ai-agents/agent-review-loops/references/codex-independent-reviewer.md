# Codex độc lập làm reviewer fallback

## Khi dùng

Dùng khi Claude và các OpenCode reviewer đều hết quota, thiếu balance, timeout hoặc unavailable. Đây là approval gate cuối, không phải implementer tự duyệt.

## Nguyên tắc độc lập

- Reviewer phải là một tiến trình Codex mới, context sạch, không `resume` session implementer.
- Không dùng subagent do chính implementer spawn làm gate chính.
- Reviewer chạy `--ephemeral --sandbox read-only` và reasoning `high`.
- Dùng model mặc định đã route đúng tới Sol; không ép alias ngắn như `-m sol` nếu route/provider chưa được smoke-test.
- Nếu reviewer có finding, mở một Codex implementer mới để sửa; sau đó mở một reviewer mới để review lại.

## Lệnh mẫu

```bash
codex exec --ephemeral --sandbox read-only \
  -c 'model_reasoning_effort="high"' \
  --output-schema tasks/codex-review-verdict.schema.json \
  --output-last-message D:/CodexRuntime/reviews/latest.json \
  "Review toàn bộ git diff so với HEAD. Không sửa file. Chỉ APPROVED nếu không còn finding cần sửa."
```

Schema nên giới hạn verdict vào `APPROVED`, `MINOR_FIXES`, `REJECT`, cùng findings có severity/file/line/issue/required_fix.

## Gate xác minh

- Không lấy JSON/trạng thái trung gian trong stream làm verdict. Codex có thể phát một object tạm khi vẫn đang điều tra.
- Chỉ nhận verdict khi process đã kết thúc bình thường và `--output-last-message` chứa JSON hợp lệ.
- Nếu process đã ghi artifact đầy đủ nhưng không tự thoát sau phần kết luận/tokens, đọc và validate artifact trước; chỉ sau đó mới dừng process.
- Reviewer read-only có thể không chạy test do sandbox; Hermes/implementer phải chạy test độc lập. Reviewer tập trung vào diff, race, lifecycle, semantics và coverage gaps.

## Windows read-only sandbox

PowerShell có thể bị sandbox Windows chặn khi khởi tạo. Cho reviewer tự chuyển sang công cụ đọc khác (ví dụ Node MCP) thay vì đổi sang quyền ghi. Nếu reviewer không đọc được diff thực tế thì verdict không hợp lệ.

## Pitfall quan trọng

Suite xanh không thay review gate. Trong watcher/recovery code, reviewer cần đặc biệt kiểm tra:

- success count có dựa trên proof đã verified hay chỉ đếm callback;
- lock takeover có giới hạn đúng dead retained owner;
- lease được giữ/release đúng suốt bounded recovery;
- serial mapping đổi khi thiết bị cũ offline có được phát hiện độc lập với callback;
- retry có giới hạn theo failure signature, không blind loop;
- timeout dạng float có chặn `nan`, `inf`, số âm.
