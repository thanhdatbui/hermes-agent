# Gate Compliance Watchdog Audit, Timezone Desync & Auto-Rewire Churn Discipline

## 1. Bối Cảnh & Vấn Đề Thực Tế
Trong hệ thống tự động hoá và Phone Farm, các Watchdog định kỳ (như `gate_compliance_watchdog.py` 6h/lần) đối soát các log audit (`logs/`, `runtime/audit_logs/`). Khi gặp sự cố báo động giả hàng loạt (112 vi phạm, 27 QUOTA, 19 TIMEOUT), qua phân tích tận gốc đã phát hiện 3 vấn đề kiến trúc điển hình:

### A. Nhiễm Dữ Liệu Test / Mock (Pytest Log Pollution)
* **Hiện tượng:** Watchdog báo 27 lỗi QUOTA, 19 lỗi TIMEOUT, 11 lỗi NEEDS_INPUT. Tuy nhiên production farm hoàn toàn không có máy nào bị cạn quota.
* **Nguyên nhân gốc:** Khi chạy unit test (`pytest tests/test_dispatch_worker.py`), các test case mock chạy trực tiếp và ghi các dòng failure giả lập vào file audit chung (`dispatch.jsonl`, `dispatch_audit.jsonl`).
* **Kỷ luật giải pháp:**
  * BẮT BUỘC watchdog phải lọc sạch các dòng test qua hàm predicate `is_test_log_line(line)`:
    ```python
    def is_test_log_line(line: str) -> bool:
        """Loại bỏ các log do pytest / mock sinh ra."""
        if not (line.startswith("{") and line.endswith("}")):
            return False
        try:
            d = json.loads(line)
            workdir = str(d.get("workdir") or d.get("cwd") or "")
            f_name = str(d.get("file") or d.get("target_file") or d.get("target") or "")
            if "pytest" in workdir or "pytest" in f_name or f_name == "target.py" or "tmp_path" in workdir:
                return True
        except Exception:
            pass
        return False
    ```

### B. Lệch Múi Giờ Naive vs UTC (Timezone Naive Desync)
* **Hiện tượng:** Báo cáo khung 00:00 - 06:00 sáng lại lôi các vi phạm từ 17:00 - 23:00 tối hôm trước vào báo cáo, dù tối hôm trước đã commit fix.
* **Nguyên nhân gốc:** Các hook ghi log bằng `datetime.now().isoformat()` tạo chuỗi timestamp không có timezone (naive local time UTC+7). Watchdog chạy giờ UTC (`datetime.now(timezone.utc)`) khi gặp chuỗi naive lại dùng `dt.replace(tzinfo=timezone.utc)`, khiến 17:50 chiều hôm trước bị hiểu nhầm thành 17:50 UTC (tức 00:50 đêm nay).
* **Kỷ luật giải pháp:**
  * Khai báo danh sách các file log ghi giờ local naive: `LOCAL_NAIVE_LOGS = {"dispatch_audit.jsonl", "console_block_audit.jsonl"}`.
  * Nếu timestamp đến từ các file này và không có `tzinfo`, quy đổi chuẩn xác từ giờ local về UTC:
    `dt = dt.astimezone().astimezone(timezone.utc)` trước khi so sánh với cửa sổ `cutoff`.

### C. Triết Lý "Cấm Khóc Lóc Block" & Đo Lường Ma Sát (Churn Metric)
* **Hiện trạng rào cản thụ động (Passive Block):**
  * `subagent_edit_blocked`: Agent gọi `delegate_task` sửa code $\rightarrow$ Hook quăng lỗi cấm $\rightarrow$ Agent loay hoay 3–5 lượt thử đổi prompt vẫn bị chặn, đốt hàng nghìn token vô ích.
  * `investigate` thiếu budget: Agent quên gõ chữ "Budget" $\rightarrow$ Hook chặn bắt gõ thêm $\rightarrow$ Mất 1–2 lượt gõ lại.
* **Kỷ luật Auto-Rewire (0-turn overhead):**
  * **Tầng 1 (Ưu tiên số 1):** Hook tự động sửa request an toàn ngay trên đường truyền.
    * Thiếu budget $\rightarrow$ Tự inject `Budget: <= 8 tool calls, timeout < 3 phút` vào prompt/args và cho phép chạy ngay.
    * Budget $> 8$ $\rightarrow$ Tự kẹp `budget = min(budget, 8)` (Auto-clamped).
    * Foreground timeout $> 60$s $\rightarrow$ Tự kẹp `timeout = min(timeout, 60)` hoặc chuyển sang background nếu là lệnh dài.
  * **Tầng 2 (Active Pivot / 1-turn):** Nếu không thể tự sửa (như `delegate_task` sửa code), Hook BẮT BUỘC trả về `next_action` chứa lệnh shell thực thi cụ thể (`python D:/Taadaa/tools/dispatch_worker.py ...`), cấm hướng dẫn suông.
* **Định lượng trên Báo Cáo Watchdog:**
  * Các lần Auto-Rewire ngầm (0-turn) KHÔNG được tính là lỗi Gate FAIL, mà ghi nhận riêng: `🔄 Auto-rewire cứu nguy: N lần`.
  * Thống kê số lượt loay hoay trung bình (Churn) bên cạnh các rule bị chặn. Rule nào có số lượt loay hoay $> 2$ lượt BẮT BUỘC phải được ưu tiên viết Auto-Rewire để triệt tiêu ma sát.

## 2. Worker Sol Budget & Micro-patching Latency
* Sol Web Worker (`gpt-web-sol` qua OmniRoute `:20129`) thường thực hiện quy trình `READ_FILE` $\rightarrow$ nhiều lượt `PATCH` nhỏ lẻ liên tiếp.
* Nếu để mặc định 8 turns và 360s floor, Sol dễ chạm `MAX_TURNS_REACHED` khi xử lý các file nhiều hàm, dẫn đến rơi rớt công việc hoặc timeout tổng.
* **Chuẩn hóa:**
  * `dispatch_worker.py`: `--max-turns` mặc định nâng lên $\ge 12$, `SOL_AGY_TIMEOUT_FLOOR` và `--timeout` mặc định nâng lên $\ge 480$s.
  * `sol_worker.py`: `DEFAULT_MAX_TURNS = 12`.
