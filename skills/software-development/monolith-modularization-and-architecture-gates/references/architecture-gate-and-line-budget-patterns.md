# Architecture Gate & Line Budget Patterns for AI Agentic Workflows

## 1. Tại sao chỉ thị prompt mềm ("Hãy giữ code sạch") luôn thất bại?
Khi code được phát triển qua nhiều phiên với nhiều mô hình AI khác nhau (Gemini, Claude, GPT):
- AI không mang trí nhớ vĩnh viễn về cấu trúc bạn từng thảo luận.
- Khi nhận yêu cầu: "Sửa lỗi proxy" hoặc "Bổ sung API TikTok mới", con đường ngắn nhất và ít kháng cự nhất của LLM là mở file orchestrator chính ra và append hàm mới trực tiếp vào cuối file.
- Sau 2-3 tuần, một file đã refactor sẽ nhanh chóng tái phình to lên 2.000 dòng.

## 2. Giải pháp: Biến ranh giới module thành bức tường vật lý trong CI / Test Suite
Thay vì hy vọng AI nhớ luật, hãy biến ranh giới thành bài test tự động:
1. **Kiểm tra ngân sách số dòng (Line Budget Assertion):**
   - Đặt trần cứng cho orchestrator (ví dụ: `download_by_niche.py` <= 1.400 dòng).
   - Nếu AI thêm code vào file tổng $\rightarrow$ Pytest fail $\rightarrow$ Closeout Gate reject $\rightarrow$ AI bắt buộc phải refactor lại vào module con mới được commit.
2. **Kiểm tra cấu trúc package (Module Existence Check):**
   - Đảm bảo danh sách các file module độc lập luôn hiện diện trên đĩa.
3. **Chống định nghĩa lại hàm domain (No Inline Redefinitions):**
   - Quét AST hoặc regex cấm xuất hiện các signature hàm nghiệp vụ (ví dụ `def format_proxy`, `def phash`) trong orchestrator. Toàn bộ logic này bắt buộc phải được import từ package con.

## 3. Mẫu Code Chuẩn Triển Khai
```python
import re
from pathlib import Path

def test_orchestrator_discipline():
    root = Path(__file__).parent.parent
    orchestrator = root / "scripts" / "orchestrator.py"
    
    # 1. Line count budget
    lines = orchestrator.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 1400, f"Orchestrator phình to: {len(lines)} > 1400 lines"
    
    # 2. Package modules
    pkg = root / "scripts" / "my_package"
    assert (pkg / "__init__.py").exists()
    assert (pkg / "proxy.py").exists()
    assert (pkg / "storage.py").exists()
    
    # 3. Forbid inline redefinitions
    code = "\n".join(lines)
    for fn in ["def handle_proxy(", "def connect_db("]:
        assert fn not in code, f"Vi phạm kiến trúc: {fn} phải được import từ package con!"
```
