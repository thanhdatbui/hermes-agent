# Session Routing Reference

## Role defaults

- Worker mặc định: Codex qua provider `omni`/9Router, model coding nhanh, reasoning cao.
- Với plan, audit/review hoặc thay đổi code quan trọng: ép worker sang model reasoning cao hơn.
- Debug project automation dưới `D:/Taadaa`: bắt đầu bằng model debug mặc định; nếu lặp không tiến triển thì escalation theo thứ tự đã cấu hình.
- Reviewer chính: Claude Opus với effort thấp cho audit/review; reviewer chỉ đọc và chạy kiểm tra, không sửa source.
- OpenCode chỉ là fallback khi reviewer chính gặp quota/provider failure.

## Windows CLI

Trong Windows CMD, dấu `\\` không phải line continuation. Dùng một dòng hoặc dấu `^`:

```cmd
codex exec -c "model_provider=omni" -m gpt-5.6-luna --full-auto "task"
```

Không dùng cú pháp shell kiểu Unix:

```cmd
codex exec \\ -c ...
```

## Provider verification

Trước task thật, chạy smoke test read-only và xác nhận output runtime có:

```text
provider: omni
model: <expected>
reasoning effort: <expected>
```

Sau đó yêu cầu response marker cố định. Nếu marker không xuất hiện, chưa coi backend đã sẵn sàng.

## Authentication distinction

App desktop login và CLI credential có thể là hai session khác nhau. Tuy nhiên nếu Codex được cấu hình qua local 9Router provider thì không chạy OAuth login để giải quyết lỗi routing; kiểm tra `model_provider`, `base_url`, endpoint `/v1/models`, rồi ép provider trong invocation nếu cần.

## Evidence contract

- Ghi output và status thực tế.
- Không gọi ad-hoc smoke test là full suite.
- Xóa script tạm sau khi verify nếu không cần giữ artifact.
- Không đưa API key/token vào report, state hoặc skill.
