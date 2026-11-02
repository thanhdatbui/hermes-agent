---
name: unified-patch-pipeline-reporting
description: "Quy chuẩn trích xuất và báo cáo kết quả Hội đồng Cố vấn (Council / Advisor Votes: Gemini, Claude, Sol) khi vận hành unified_patch_pipeline.py."
version: 1.0.0
platforms: [windows, linux]
metadata:
  hermes:
    tags: [pipeline, unified-patch, council, advisor, reporting, taadaa]
---
# Unified Patch Pipeline Reporting Discipline

## 1. Trigger Conditions
Áp dụng mỗi khi Coordinator kích hoạt pipeline cơ giới hóa sửa code:
```bash
python D:/Taadaa/tools/unified_patch_pipeline.py run --repo <repo> --file <target_file> --task "<task>" ...
```

## 2. Invariant Bắt Buộc (User Expectation)
- **CẤM giấu kết quả Hội đồng Cố vấn**: Ở bước S1 Plan, hệ thống triệu tập 3 Advisor (Argon/Gemini, Claude Sonnet, Sol).
- Khi pipeline trả về kết quả, Coordinator **BẮT BUỘC** trích dẫn chi tiết bảng biểu quyết đồng thuận (Council Votes) trong báo cáo gửi User, tuyệt đối không được chỉ báo "PLAN: OK" rồi bỏ qua.

## 3. Cấu Trúc Báo Cáo Chuẩn

```markdown
### 🗳️ BÁO CÁO ĐỒNG THUẬN HỘI ĐỒNG ADVISOR (COUNCIL VOTES)
- **Kết quả biểu quyết**: ĐỒNG THUẬN X/3 (Tỷ lệ %)
- **Thời gian lập plan**: <N>s
- **Phương án được chọn thi công**: <Tên Advisor> (Lý do chọn theo thứ tự ưu tiên)

| Thành viên Advisor | Trạng thái | Độ trễ (Latency) | Số Edit | Đánh giá / Tóm tắt phương án |
| :--- | :---: | :---: | :---: | :--- |
| **Argon (Gemini)** | `OK` / `FAIL` | ...s | ... | ... |
| **Claude Sonnet** | `OK` / `FAIL` | ...s | ... | ... |
| **Sol** | `OK` / `FAIL` | ...s | ... | ... |

📋 **Nội dung Contract chính được thông qua:**
- Edit 1: <file> -> <tóm tắt contract O(1)>
```

## 4. Nguồn Dữ Liệu
- Đọc từ output stdout: trường `COUNCIL VOTES:`.
- Hoặc đọc từ state artifact: `D:/Taadaa/runs/<run_id>/plan.json` (các trường `planner`, `consensus_summary`, `council_details`, `edits`).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
