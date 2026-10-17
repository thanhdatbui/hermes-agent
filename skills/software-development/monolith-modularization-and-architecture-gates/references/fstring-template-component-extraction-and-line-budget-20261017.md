# Kỹ Thuật Tách Component Template Khỏi Monolith F-String Để Giữ Vững Trần Line Budget

## 1. Bối cảnh & Cạm Bẫy Monolith Template F-String (`tiktok_dashboard.py`)

Khi phát triển thêm tính năng UI trên các dashboard Python sử dụng cơ chế inlined HTML/JS trong chuỗi f-string (ví dụ: `tiktok_dashboard.py`):
1. **Trần Line Budget cứng của Architecture Gate (`< 3000 lines`):**
   - File `tiktok_dashboard.py` đang ở mức 2.914 dòng và bị giám sát bởi unit test `test_dashboard_architecture_gate.py` (`assert line_count < 3000`).
   - Nếu viết thêm một Modal HTML phức tạp kèm mã JavaScript tương tác (150–200 dòng) trực tiếp vào trong file, tổng số dòng sẽ lập tức vượt ngưỡng 3.000 dòng và làm gãy CI/Architecture Gate ngay lập tức.
2. **Cạm bẫy thoát ký tự ngoặc nhọn kép trong Python F-String (`{{` vs `{`):**
   - Trong chuỗi `html = f"""..."""`, toàn bộ mã CSS và JavaScript bắt buộc phải nhân đôi dấu ngoặc nhọn: `function foo() {{ ... }}`.
   - Khi viết mã JS dài (xử lý sự kiện, fetch API, render bảng DOM, lọc tìm kiếm), việc nhân đôi hàng trăm dấu `{` và `}` cực kỳ dễ sót, gây ra lỗi `KeyError` hoặc cú pháp `f-string: unmatched '{'` lúc runtime.

---

## 2. Kỹ Thuật Tách Component Độc Lập (Componentized Injection Pattern)

Thay vì chèn trực tiếp khối HTML/JS khổng lồ vào thân file orchestrator, giải pháp chuẩn hóa là:

### Bước 1: Tạo Module Component Chuyên Biệt trong Thư Mục Con
Tạo file `dashboard/<feature>_component.py` (ví dụ: `dashboard/follow_detail_component.py`):
- Khai báo các hằng số chuỗi chuẩn `FOLLOW_DETAIL_MODAL_HTML` và `FOLLOW_DETAIL_MODAL_JS`.
- **Ưu điểm vượt trội:**
  * Toàn bộ mã HTML và JavaScript được viết bằng cú pháp tiêu chuẩn với `{` và `}` đơn, không cần nhân đôi `{{` hay `}}`.
  * Có docstring và cú pháp Python độc lập, được kiểm tra cú pháp sạch sẽ qua `py_compile`.
  * Tách biệt hoàn toàn logic giao diện của tính năng mới khỏi monolith chính.

```python
# -*- coding: utf-8 -*-
# dashboard/follow_detail_component.py

FOLLOW_DETAIL_MODAL_HTML = """
    <div id="followDetailModal" class="modal-backdrop" style="display:none;" onclick="handleFollowDetailModalBackdropClick(event)">
        <div class="modal-card">
            ...
        </div>
    </div>
"""

FOLLOW_DETAIL_MODAL_JS = """
    let currentFdData = null;

    async function openFollowDetailModal(machine, row, username) {
        const res = await fetch(`/api/follow-detail?machine=${machine}&row=${row}`);
        const data = await res.json();
        renderFollowDetailModal(data);
    }

    function renderFollowDetailModal(data) {
        // Viết mã JavaScript tự nhiên với { và }, không lo lỗi f-string
    }
"""
```

### Bước 2: Import & Inject Bằng Biến F-String Trong Monolith
Trong file monolith (`tiktok_dashboard.py`):
1. Import các hằng số component:
   ```python
   from dashboard.follow_detail_component import (
       FOLLOW_DETAIL_MODAL_HTML,
       FOLLOW_DETAIL_MODAL_JS,
   )
   ```
2. Chèn biến vào vị trí mong muốn trong chuỗi `html = f"""..."""`:
   - Vị trí chèn Modal HTML: `{FOLLOW_DETAIL_MODAL_HTML}`
   - Vị trí chèn Script JS: `{FOLLOW_DETAIL_MODAL_JS}`

### Cơ chế hoạt động của Python F-String:
Khi Python biên dịch chuỗi `f"""...{FOLLOW_DETAIL_MODAL_JS}..."""`:
- Python đánh giá biểu thức bên trong `{...}` là biến `FOLLOW_DETAIL_MODAL_JS`.
- Giá trị chuỗi của biến được **thay thế nguyên văn (verbatim substitution)** vào chuỗi HTML kết quả.
- Python **tuyệt đối không phân tích cú pháp lại các dấu `{` và `}`** nằm bên trong chuỗi giá trị của biến. Do đó, mã JavaScript bên trong component giữ nguyên 100% tính toàn vẹn mà không bị lỗi f-string!

---

## 3. Lợi Ích Đo Lường Được

1. **Bảo toàn Architecture Line Budget:**
   - File `tiktok_dashboard.py` chỉ tăng thêm vỏn vẹn ~15 dòng (import, 2 dòng inject `{...}`, 2 nút bấm và 1 endpoint routing trong `do_GET`), giữ tổng số dòng ở mức ~2.929 dòng (dưới trần 3.000 dòng).
   - Module `dashboard/follow_detail_component.py` nhận trọn ~230 dòng mã UI và quản lý độc lập.
2. **Không lo đụng độ Git Diff:**
   - Khi nhiều worker hoặc agent cùng làm việc, việc thêm UI vào component riêng giúp diff của monolith cực kỳ nhỏ gọn (< 25 dòng), tránh xung đột merge và tuân thủ tuyệt đối ngân sách diff của `closeout_gate.py` (`<= 30.000 bytes`).
