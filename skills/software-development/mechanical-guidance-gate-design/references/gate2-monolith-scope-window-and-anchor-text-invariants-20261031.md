# Gate 2 Monolith Architecture: Scope Window Anchor vs Span Lines Trap (2026-10-31)

## 1. Bản Chất Sự Cố Cơ Giới Hóa Gate 2 (2026-10-31)
- **Thiết kế ban đầu (commit `abbaaf5`):** Nhằm ngăn chặn Coordinator ném prompt mở/lười biếng (`refactor`, `rewrite`, `toàn bộ file`) vào các file monolith > 1.500 dòng, Gate 2 được cài đặt kiểm tra cơ học:
  1. File > 1.500 dòng.
  2. Bắt buộc có symbol anchor (`def/class <symbol>`).
  3. Đo độ dài hàm theo thụt đầu dòng: `span_len = e_idx - s_idx`. Nếu `span_len > 150 dòng` -> ném lỗi `SPAN_TOO_BIG` và thoát `exit(3)`.
- **Cái bẫy cơ học (Deadlock):**
  - Gate 2 chạy ở bước **Pre-check (trước khi thi công)**, chưa hề có git diff thực tế.
  - Trong các codebase thực chiến lớn, các hàm điều phối luồng chính (như `run_mode2`, `run_all`, `dispatch_pipeline`) rất thường dài từ **200 đến 500 dòng**.
  - Việc lấy **toàn bộ độ dài của hàm gốc (`span_len`)** làm đại diện cho **phạm vi thay đổi (`diff size`)** là sai lệch bản chất. Khi task chỉ yêu cầu sửa đúng 6 dòng bên trong 1 vòng lặp con, Gate 2 nhìn thấy `run_mode2` dài 448 dòng liền phán `SPAN_TOO_BIG (448 > 150)` và chặn đứng tại cửa, làm tê liệt hoàn toàn pipeline tự động.

---

## 2. Kiến Trúc Chuẩn Hóa Theo Tư Vấn Claude Code CLI (Approved 88/100)

### A. Nguyên tắc phân lớp:
1. **Không thay thế Symbol Anchor bằng Text Anchor mù:** Symbol anchor (`def/class`) vẫn là chốt chặn xác định đúng hàm/ngữ cảnh cần sửa.
2. **Cơ chế Scope Window 2 tầng khi hàm > 150 dòng:**
   - Khi hàm gốc `<= 150 dòng`: Vùng can thiệp cho phép `scope = (s_idx, e_idx)`.
   - Khi hàm gốc `150 < span_len <= 600 dòng`: BẮT BUỘC cung cấp thêm `--anchor-text "<chuỗi 1 dòng duy nhất >= 12 ký tự nằm trong hàm>"`. Hệ thống sẽ tạo một **Cửa sổ hẹp (Scope Window) $\pm 30$ dòng** quanh vị trí dòng text này:
     $$\text{scope} = (\max(s\_idx, t\_hits[0] - 30), \min(e\_idx, t\_hits[0] + 30))$$
   - Khi hàm gốc `> 600 dòng`: Chặn đứng tuyệt đối (`exit 3`), bắt buộc phải bóc tách refactor hàm trước khi sửa.

### B. Mẫu mã nguồn tích hợp vào `verify_gate2_monolith` (`dispatch_worker.py`):
```python
MAX_SPAN_PLAIN, MAX_SPAN_HARD, WINDOW = 150, 600, 30
scope = None
if span_len > MAX_SPAN_PLAIN:
    needle = (anchor_text or "").strip()
    t_hits = [i for i, l in enumerate(lines) if needle and needle in l]
    ok = (span_len <= MAX_SPAN_HARD and len(needle) >= 12
          and len(t_hits) == 1 and s_idx <= t_hits[0] < e_idx)
    if not ok:
        err = {
            "gate": "GATE_2_MONOLITH", "reason": "SPAN_TOO_BIG",
            "file": str(target), "symbol": symbol, "span_lines": span_len,
            "text_hits": len(t_hits),
            "hint": f"Hàm '{symbol}' dài {span_len} dòng (vượt 150 dòng). Bắt buộc truyền --anchor-text '<dòng text duy nhất >=12 ký tự nằm trong hàm>' để khóa chặt vị trí sửa cho worker (hàm > {MAX_SPAN_HARD} dòng thì bắt buộc tách hàm trước).",
        }
        return False, f"Symbol '{symbol}' span {span_len} needs unique anchor-text", err
    scope = (max(s_idx, t_hits[0] - WINDOW), min(e_idx, t_hits[0] + WINDOW))
else:
    scope = (s_idx, e_idx)
```

### C. Invariant Bắt Buộc Khi Forward Prompt Sang Worker:
- **Khối skill injection:** Thường dựng lại `effective_prompt = f"{inj.context_block}\n\n---\n[TASK CONTRACT]\n{args.prompt}"`.
- **Quy tắc bất biến:** Khối gắn `[EXACT_ANCHOR_TEXT: <needle>]` **BẮT BUỘC PHẢI GẮN SAU CÙNG (sau khối skill injection)**:
  ```python
  if getattr(args, "anchor_text", None):
      effective_prompt = f"[EXACT_ANCHOR_TEXT: {args.anchor_text.strip()}]. {effective_prompt}"
  ```
- Điều này đảm bảo tiền tố neo vị trí sửa không bao giờ bị context skill ghi đè, worker ở mọi tier đều nhìn thấy vị trí cần sửa ngay lập tức.

---

## 3. Invariant Chống Ảo Giác "Hết Nick Trong Anchor" (Farm Investigation)
- **Quy tắc điều tra Anchor:** Khi máy gặp lỗi dừng cào hoặc không đủ quota follow, CẤM TUYỆT ĐỐI Coordinator tự suy diễn giả thuyết "anchor hết nick".
- **Thực tế kỹ thuật:** Anchor nòng cốt của farm luôn có từ 150 đến hàng nghìn following/follower. Lỗi dừng cào luôn xuất phát từ:
  1. Script `break` vội vã khi gặp 1 nick con bị lag UI (`MANUAL_REVIEW: verify row sau tap không xác định`). Phải `continue` bỏ qua nick đó để duyệt nick tiếp theo.
  2. Bị đụng trần thời gian (Hard Deadline 20 phút) do fallback sang Module 1 gõ search từng nick.
  3. Bị chặn bởi cơ chế an toàn hoặc bộ lọc trùng lặp của script.
