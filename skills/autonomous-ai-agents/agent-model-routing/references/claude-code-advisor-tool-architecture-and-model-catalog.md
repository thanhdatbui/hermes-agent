# Claude Code Native Advisor Strategy & Model Catalog Architecture (v2.1.281+)

## 1. Bản chất & Nguồn gốc tính năng Advisor trong Claude Code

Anthropic giới thiệu **Advisor Strategy**: Executor (model nhanh, tiết kiệm như Sonnet/Haiku) điều phối chính và chạy tool loop end-to-end. Khi gặp quyết định phức tạp, lỗi mơ hồ hoặc bế tắc xoay vòng, executor tự động gọi Advisor (Opus) ở server-side để xin định hướng kế hoạch mà không cần phân rã thủ công thành multi-agent orchestrator.

Trong Claude Code CLI (từ v2.1.x, kiểm chứng trên `v2.1.281`), tính năng này đã được tích hợp sẵn dưới dạng **lệnh slash tương tác `/advisor`** và cờ cấu hình `advisorModel`.

---

## 2. Model Catalog: Sự thật về Tên Model vs Nhầm lẫn Cộng đồng

Trên mạng xã hội (Facebook/Twitter), cộng đồng thường lan truyền công thức:
> *"Để model chính Sonnet 5.5 rồi dùng lệnh /advisor chọn Opus 5.5..."*

### Đối soát thực tế trong Binary & Model Catalog của Claude Code v2.1.281:
- **Sonnet:** Bản mới nhất trong catalog là **`Sonnet 5`** (`claude-sonnet-5`). **HOÀN TOÀN KHÔNG CÓ `Sonnet 5.5`** trong catalog chính thức. Cộng đồng nhầm lẫn do quen miệng ghép đuôi `.5` theo Opus 5.5.
- **Opus:** Model cao cấp nhất là **`Opus 5.5`** (`claude-opus-5-5`).
- **Fable:** Model `Fable 5.1` (`claude-fable-5-1`).
- Danh sách hợp lệ cho lệnh `/advisor`: `["fable", "opus", "sonnet", "off"]`.

---

## 3. Quy tắc Thứ bậc Bắt buộc (Advisor Capability Invariant)

Mã nguồn Claude Code kiểm tra chặt chẽ thứ bậc năng lực giữa model chính và advisor (`woe(mainModel, advisorModel)`):
1. **Advisor phải có năng lực cao hơn hoặc bằng Main Model:**
   - Advisor rank của Advisor phải nhỏ hơn hoặc bằng (rank 1 cao nhất) rank của Main Model.
   - Nếu Main Model là **Opus 5.5**, việc chọn Opus làm Advisor sẽ bị vô hiệu hóa trên main loop với thông báo:
     > *"Advisor will not activate on the main model (advisor is less capable); subagents may still use it..."*
2. **Cặp đôi tối ưu chuẩn (Recommended Setup):**
   - **Main Model:** `Sonnet 5` (`claude-sonnet-5` hoặc alias `sonnet`).
   - **Advisor Model:** `Opus 5.5` (`claude-opus-5-5` hoặc alias `opus`).
   - Mô hình này mang lại hiệu năng tư duy tiệm cận Opus với chi phí token và tốc độ gần mức Sonnet.

---

## 4. Cách cấu hình

### Cách 1: Thao tác trong phiên TUI Interactive của Claude Code
1. Chuyển model chính về Sonnet:
   ```text
   /model sonnet
   ```
2. Kích hoạt Advisor Opus:
   ```text
   /advisor opus
   ```
   *(Để tắt: `/advisor off`)*

### Cách 2: Cấu hình tĩnh trực tiếp trong `~/.claude/settings.json`
Chỉnh sửa file cấu hình toàn cục `C:\Users\<User>\.claude\settings.json`:
```json
{
  "model": "claude-sonnet-5",
  "advisorModel": "claude-opus-5-5"
}
```

---

## 5. Pitfalls khi kiểm tra & điều phối

1. **`claude --help` và `claude -p` không hiển thị slash commands:**
   - Chạy `claude -p '/help'` sẽ trả về: `"/help isn't available in this environment."` vì print mode không khởi tạo runtime tương tác.
   - Đừng vội kết luận CLI không hỗ trợ tính năng chỉ vì `--help` không liệt kê `/advisor`. Slash commands được xử lý động trong Ink UI runtime.
2. **Tránh kiểm tra lan man, lạc đề (User Correction Lesson):**
   - Khi người dùng gửi ảnh yêu cầu kiểm tra tính năng cụ thể (Advisor), phải nhắm thẳng vào cờ/lệnh đó. Không tự ý kiểm tra các model/tính năng không được yêu cầu (như Fable) gây loãng câu trả lời.
   - Bằng chứng thực tế (chụp ảnh cửa sổ TUI thật, đọc cấu hình json thật) có giá trị cao nhất.
