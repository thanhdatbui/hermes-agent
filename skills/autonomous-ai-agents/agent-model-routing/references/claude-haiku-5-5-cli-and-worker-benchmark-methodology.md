# Claude Haiku 5.5 CLI Execution & Worker Benchmark Methodology (14/10/2026)

## 1. Claude Code CLI (v2.1.281+) Direct Execution with Uncataloged Models
- **Truyền model ID trực tiếp**: Claude Code CLI cho phép truyền các model string chưa có trong alias mặc định như `--model claude-haiku-5-5`.
- **Hành vi Runtime**:
  + CLI xuất cảnh báo không chặn: `[claude-code:unrecognized_model]` và áp dụng context window 200k mặc định.
  + Request được chuyển tiếp nguyên vẹn lên First-Party Anthropic API, trả về `canonicalModel: "claude-haiku-5-5"`.
- **Thinking / Extended Reasoning Support**:
  + Cờ `--effort medium` và `--effort high` hoạt động trực tiếp trên `claude-haiku-5-5`.
  + Thinking tokens được hạch toán đầy đủ trong `usage.output_tokens_details.thinking_tokens`.

## 2. Invariants khi Chạy One-Shot Benchmark / Worker Evaluation trên Windows
- **Khóa Tool `--tools ""`**: Với các bài test đánh giá năng lực code/surgery one-shot, bắt buộc truyền `--tools ""` để ngăn model tiêu hao turn vào các tool mặc định (`Read`, `Bash`).
- **Tránh bẫy Pipe MSYS / Git-Bash**: Truyền prompt trực tiếp qua argument CLI hoặc qua file trong script Python subprocess thay vì pipe `cat | claude -p`, tránh treo tiến trình Node.js trên Windows.
- **Trích xuất JSON có cấu trúc**:
  ```bash
  claude -p "<prompt>" --model claude-haiku-5-5 --effort medium --tools "" --output-format json
  ```
  Cho phép đo lường chính xác `duration_api_ms`, `thinking_tokens`, `input_tokens`, `output_tokens` và `total_cost_usd`.

## 3. Cấu trúc Giải Đấu Worker 2 Giai Đoạn (2-Stage Tournament)
- **Giai đoạn 1 (Nội chiến mức suy luận)**: Đấu đối kháng giữa các mức reasoning (`medium` vs `high`) trong cùng họ model (ví dụ `Claude Haiku 5.5`) để chọn ra điểm cân bằng tối ưu giữa độ sâu tư duy và tốc độ/chi phí.
- **Giai đoạn 2 (Chung kết so găng)**: Quán quân Giai đoạn 1 so tài với Worker chuẩn của Farm (`Gemini 3.8 Flash Medium` qua proxy OmniRoute `:20129` `ag-gemini-pool-3`).
- **3 Trụ Cột Đánh Giá Cho Worker Phone Farm**:
  1. *Atomic File State Update*: Ghi nguyên tử qua tempfile cùng thư mục + `os.replace` + phòng thủ `PermissionError` trên Windows do file indexer / antivirus.
  2. *Defensive UI XML Parsing*: Parse ATX / UIAutomator XML an toàn chống crash khi bị cắt cụt, trích xuất bounds regex và kẹp tọa độ (clamp) trong màn hình.
  3. *O(1) Scope Lock Bug Surgery*: Sửa chính xác bug tiềm ẩn với diff tối thiểu ($\le 15$ dòng), không thêm dependency ngoài, không over-engineering.
