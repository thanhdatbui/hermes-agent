# Semantic Canary Engine & Code Path Activation Discipline (2026-10-30)

## 1. Bản Chất Bệnh "Canary Hình Thức" (Pro-Forma Canary)
- **Triệu chứng:** Sửa một lỗi logic nghiệp vụ sâu (ví dụ: tab fallback từ Friends/Following sang For You khi feed rỗng), nhưng runner Canary lại chạy lệnh generic cố định (`--recovery-test-swipes 2`).
- **Hậu quả:** 
  - Máy chỉ mở app, verify profile, vuốt 2 video For You rồi báo exit 0 và `CANARY_VERDICT: PASSED`.
  - Nhánh code fallback vừa sửa **hoàn toàn chưa hề được kích hoạt** trên thiết bị thật.
  - Phản ứng của Operator: *"Ủa t đã ép cổng run canary phải chạy đúng cái lỗi vừa vá mà? Hàm canary t muốn chạy đúng bản vá của session h làm sao. Đéo đc thì gắn não llm cho nó khôn đi"*.

## 2. Vì Sao Rule Tĩnh / Regex Thất Bại Trước Độ Phức Tạp Ngữ Nghĩa
- Monolith runner (`feed_swipe_smoke.py`, `upload_workflow`, `login_v1`) có hàng trăm nhánh rẽ logic khác nhau.
- `canary_matrix.json` chỉ đọc file path glob (ví dụ `**/flows/feed*`), gán nhãn thô `feed-swipe` và chạy tham số hardcode.
- Càng cố viết luật tĩnh thì càng sinh ra hàng nghìn if/else mà vẫn bị lọt lưới.
- **Giải pháp bắt buộc:** Gắn não LLM (Semantic Canary Planner) để đọc hiểu ngữ nghĩa trực tiếp từ `git diff`.

## 3. Kiến Trúc 2 Chặng: Semantic Canary Engine

```
Git Diff ──▶ canary_plan.py (--semantic) ──▶ canary_runner.py ──▶ .canary_receipt.json
              (LLM phân tích diff,               (Chèn cli_args_override,  (Receipt v2 ghi nhận
               sinh cli_args_override +           chạy máy thật, đối soát   semantic_verified: true)
               log_assertions)                    log.jsonl bắt buộc)
```

### Chặng 1: Semantic Canary Planning (`tools/canary_plan.py`)
- Lấy `git diff base HEAD`.
- Gọi LLM (Claude CLI / OmniRoute) phân tích code delta và sinh ra:
  1. `target_flow`: Tên flow logic vừa sửa.
  2. `cli_args_override`: Danh sách cờ CLI ép máy thật chạy vào đúng nhánh đó (ví dụ: `--feed-distribution '{"for-you": 0.0, "following": 1.0, "friends": 0.0}'`, `--recovery-test-swipes 4`).
  3. `log_assertions`:
     - `required_patterns`: Danh sách chuỗi/regex bắt buộc phải xuất hiện trong `log.jsonl` hoặc `summary.txt` chứng minh code path đã thực sự chạy qua (kèm `min_matches`).
     - `forbidden_patterns`: Danh sách chuỗi lỗi cấm xuất hiện.
  4. `ocr_spec`: Từ khóa bắt buộc trên màn hình nghiệm thu sau khi ca hoàn tất.
- Lưu payload `semantic` vào `canary_plan.json` (schema 2).

### Chặng 2: Mechanical Log Verification (`tools/canary_runner.py`)
- Runner tự động nạp `cli_args_override` từ `canary_plan.json` (thay placeholder `<N>` bằng máy, `<row>` bằng row).
- Khi tiến trình trên máy kết thúc exit 0:
  - Runner quét file `log.jsonl` và `summary.txt` trong run artifacts.
  - **Kiểm tra `required_patterns`:** Số pattern khớp phải $\ge min\_matches$. Nếu không đạt $\rightarrow$ **ĐÁNH RỚT CANARY NGAY LẬP TỨC**:
    `[CANARY_FAIL] Máy N SEMANTIC_ASSERTION_FAILED: Nhánh code vừa sửa chưa được kích hoạt!`
  - **Kiểm tra `forbidden_patterns`:** Nếu có bất kỳ lỗi cấm nào $\rightarrow$ **ĐÁNH RỚT NGAY LẬP TỨC**.
- Chỉ khi nào code path được chứng minh đã kích hoạt thành công trên log và màn hình OCR đạt chuẩn mới xuất `CANARY_VERDICT: PASSED`.
