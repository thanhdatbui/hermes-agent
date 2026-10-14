# Claude Code Haiku 5.5 vs Sonnet 5: Benchmark, Advisor Latency Trap & Worker Economics (14/10/2026)

## 1. Bối cảnh & Hiện tượng bí ẩn trong Benchmark Claude Code CLI

Trong phiên đo lường thực chiến đối đầu giữa **Claude Haiku 5.5** và **Claude Sonnet 5** cho vai trò Worker sửa code Phone Farm:
- **Haiku 5.5**: Phản hồi cực nhanh (**6.5s – 15.6s**), diff O(1) chuẩn mực.
- **Sonnet 5**: Ban đầu bị ngâm turn nghiêm trọng (**56.8s – 103.1s**, chậm gấp 5 đến 16 lần), thậm chí ở bài toán sửa proxy kiểm tra IP farm, Sonnet bật cờ đạo đức từ chối thực thi (Compliance Refusal).

---

## 2. Phát hiện Gốc rễ: Cạm bẫy Advisor ngầm (`advisorModel` trong `settings.json`)

### A. Cơ chế `advisorModel` toàn cục
Khi người dùng từng chạy lệnh `/advisor` trong phiên tương tác (TUI) của Claude Code CLI, cấu hình `"advisorModel": "sonnet"` được ghi cố định vào `~/.claude/settings.json`. Cấu hình này tự động nạp cho mọi lệnh headless `claude -p`.

### B. Sự bất đối xứng trong Benchmark (Unfair Benchmark Trap)
1. **Với Haiku 5.5:** Model ID `claude-haiku-5-5` chưa được đăng ký trong bảng xếp hạng advisor nội bộ của binary Claude Code v2.1.281 $\to$ CLI tự động in cảnh báo và **vô hiệu hóa Advisor** (`Warning: Advisor disabled...`). Haiku chạy thẳng 1-shot với 100% công lực.
2. **Với Sonnet 5:** Claude Code nhận diện `advisorModel: "sonnet"` $\to$ Trên các task kỹ thuật phức tạp, Executor Sonnet **tự động triệu tập thêm một Sonnet Advisor ngầm** (`advisor_message`).
   - Riêng lượt hội chẩn ngầm này nuốt **13.395 input tokens + 4.073 output tokens**.
   - Thời gian chờ kéo dài từ 6s lên 56s – 103s.
   - Khi hai con Sonnet thảo luận với nhau về logic kiểm tra IP và proxy, chúng tự phóng đại rủi ro bảo mật (Compliance Paranoia) dẫn đến việc **từ chối sửa code**.

### C. Giải phóng 100% công lực Sonnet bằng `--settings '{"advisorModel":"off"}'`
Khi ghi đè tắt Advisor qua cờ CLI:
```bash
claude -p "..." --model sonnet --settings '{"advisorModel":"off"}'
```
- **Bài 1 (Atomic Lease Renewal):** Sonnet giảm từ **56.8s xuống 6.48s** (nhanh hơn Haiku 10.8s!).
- **Bài 2 (UI XML Bounds Clamp):** Sonnet giảm từ **103.1s xuống 6.47s** (hòa tuyệt đối với Haiku).
- **Bài 3 (Proxy Code Surgery):** Sonnet giải quyết trong **28.5s**, **hoàn toàn hết bị từ chối**, diff cực sạch và phân loại exception (`HTTPError`, `RequestException`, `JSONDecodeError`) chuẩn Senior hơn Haiku.

---

## 3. Worker Economics: Haiku vs Sonnet trên Tài khoản Claude Pro

| Tiêu chí | Claude Haiku 5.5 (Pure) | Claude Sonnet 5 (Advisor OFF) |
| :--- | :--- | :--- |
| **Tốc độ thực thi** | 6.5s – 15.6s | 6.48s – 28.5s |
| **Giá token API niêm yết** | $0.80 / $4.00 per MTok | $3.00 / $15.00 per MTok (đắt gấp 3.75x) |
| **Bào mòn Quota 5h Pro** | Rất thấp (~1.000–2.000 thinking tokens) | Nặng hơn gấp 3–4 lần (tính theo Compute Weight) |
| **Độ sâu phân loại lỗi** | Đủ chuẩn O(1) farm, thực dụng | Senior xuất sắc, phân tích race condition sâu |
| **Khuyến nghị vai trò** | **Worker thi công mặc định hằng ngày** | **Worker giải bài toán thuật toán/concurrency khó** |

---

## 4. Nghịch lý Haiku + Advisor: Cạm bẫy phá hủy kinh tế

Nếu cố tình bật Advisor cho Haiku:
1. **Anthropic cấm Haiku làm Advisor:** Binary chỉ cho phép `["opus", "sonnet", "fable", "off"]`.
2. **Kinh tế bị phá sản:** Haiku giá rẻ ($0.80) khi gọi cố vấn Sonnet ($3.00) hoặc Opus ($15.00) sẽ kéo theo toàn bộ context 10k–15k tokens sang model cố vấn. Lượt cố vấn đó bị tính tiền và trừ quota Pro theo biểu giá của model đắt tiền.
3. **Quy tắc vàng:** **Haiku 5.5 BẮT BUỘC DÙNG ĐƠN ĐỘC (Advisor OFF)** để bảo toàn tốc độ 10s và chi phí siêu rẻ.
