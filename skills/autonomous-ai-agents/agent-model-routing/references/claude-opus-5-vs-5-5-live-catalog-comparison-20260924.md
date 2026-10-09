# So sánh Claude Opus 5 vs Claude Opus 5.5 & Bài học kiểm tra Live Catalog — 24/09/2026

## 1. Sự cố phán đoán sai & Bài học Live Verification
- **Sự cố**: Khi User hỏi về `Claude Opus 5.5` ("app claude bth t mở đc opus 5.5 r mà"), Agent ban đầu dựa vào knowledge cutoff cũ và local binary `claude.exe` (chưa sync model alias mới) để vội vàng kết luận "không tồn tại Claude Opus 5.5".
- **Bị User chỉnh đốn**: User có gói Claude Pro và yêu cầu test thực tế.
- **Thực tế sau khi truy vấn Live Catalog**:
  - Truy vấn OpenRouter API (`https://openrouter.ai/api/v1/models`) và OmniRoute `:20129`: **`anthropic/claude-opus-5.5` hoàn toàn CÓ THẬT**, được phát hành chính thức ngày **21/09/2026** (canonical slug: `anthropic/claude-opus-5.5-20260921`).
- **Quy tắc sống còn**:
  - TUYỆT ĐỐI CẤM Agent khẳng định một model AI không tồn tại chỉ dựa vào kiến thức huấn luyện cũ hay binary CLI cục bộ.
  - Khi User nhắc tới một model mới, BẮT BUỘC query live API router (`http://192.168.110.123:20129/v1/models`, OpenRouter `/api/v1/models`) để lấy ground truth trước khi trả lời.

## 2. Bảng so sánh chi tiết Opus 5 vs Opus 5.5 (Trích xuất từ API spec thật)

| Tiêu chí | Claude Opus 5 (`20260723`) | Claude Opus 5.5 (`20260921` — MỚI) | Bước nhảy |
| :--- | :--- | :--- | :--- |
| **Ngày phát hành** | 23/07/2026 | **21/09/2026** | Phiên bản kế nhiệm trực tiếp |
| **Intelligence Index** *(Artificial Analysis)* | `50.8` | **`57.6`** | **Tăng vọt 6.8 điểm** |
| **Cơ chế Reasoning** | Tùy chọn (`mandatory: false`) | **Bắt buộc (`mandatory: true`)** | Luôn chạy qua thinking tokens (low $\to$ max) |
| **Trọng tâm tối ưu** | End-to-end software, bug finding | **Multi-step changes in large codebases** | Chuyên trị sửa code codebase lớn |
| **Agentic Capability** | Bounded tasks | **Long-horizon agentic work** | Giữ context và contract dài hơi |
| **Context Window** | 1,000,000 tokens (1M) | **1,000,000 tokens (1M)** | Chuẩn 1M context |
| **Max Output Tokens** | 128,000 tokens | **128,000 tokens** | Đủ sinh module hoàn chỉnh |
| **Giá Input Token** | $5.00 / 1M tokens | **$4.00 / 1M tokens** | **Rẻ hơn 20%** |
| **Giá Output Token** | $25.00 / 1M tokens | **$20.00 / 1M tokens** | **Rẻ hơn 20%** |
| **Giá Cache Read** | $0.50 / 1M tokens | **$0.20 / 1M tokens** | **Rẻ hơn 60%** (tối ưu cực lớn cho Agent loop) |

## 3. Bản đồ Model Claude Anthropic (Tính đến cuối tháng 09/2026)
- **Claude Sonnet 4.6**: Model "ngựa thồ" cho coding & agent loop nhanh, cân bằng giá/tốc độ.
- **Claude Opus 4.8 / Opus 5**: Flagship reasoning sâu thế hệ 4.x/5 ban đầu.
- **Claude Opus 5.5**: Flagship reasoning cao cấp nhất với **Mandatory Reasoning**, tối ưu refactor codebase lớn và long-horizon agentic.
- **Claude Fable 5**: Dòng mô hình thế hệ 5 thử nghiệm (yêu cầu usage credits riêng).
