# Thế Kiềng 3 Chân Cơ Học: Hook vs Guard vs Gate & Kiểm Tra Xung Đột 2 Tầng (18/10/2026)

## 1. Phân Biệt Rõ Ràng: Hook vs Guard vs Gate

Hệ thống kiểm soát và an toàn cơ học của Taadaa Farm được xây dựng trên mô hình 3 tầng khép kín:

```text
       [TOOL CALL CỦA AGENT]
                 │
                 ▼
┌─────────────────────────────────┐
│  1. HOOK (Bộ cảm biến / Cửa ngõ) │  <-- "Cửa an ninh quét kim loại"
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  2. GUARD (Luật cấm / Bộ lọc)   │  <-- "Quy định cấm mang dao/súng"
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│  3. GATE (Cổng kiểm chứng / Bar)│  <-- "Thẻ từ quẹt qua cửa / Nghiệm thu"
└────────────────┬────────────────┘
                 ▼
         [THỰC THI TRÊN FARM]
```

### A. Hook (Event Interceptor — Cảm biến đón chặn)
- **Bản chất:** Là cơ chế móc vào vòng đời thực thi của agent (`PreToolUse`, `PostToolUse`).
- **Nhiệm vụ:** Đón bắt mọi hành động của Agent ngay trước khi lệnh chạm tới hệ điều hành. Ví dụ: Agent vừa bấm gọi `terminal`, Hook lập tức tóm lấy gói tin JSON `(tool_name, args)` để kiểm tra.
- **Vị trí:** Nằm tại thư mục hook hệ thống trước khi lệnh chạy.

### B. Guard (Policy Enforcer — Bộ luật cấm cơ học)
- **Bản chất:** Là nội dung quy tắc cấm đoán nằm bên trong Hook hoặc Wrapper. Nó mang tính chất **CẤM ĐOÁN TUYỆT ĐỐI (Default-Deny)**.
- **Nhiệm vụ:** Nếu phạm luật là chém chết ngay tại chỗ, không có ngoại lệ:
  * `guard_broad_grep.py`: Cấm quét đĩa diện rộng (`os.walk`, `grep -r`, `find`), cấm `timeout > 60s` ở foreground.
  * `guard_android_proxy.py`: Cấm đặt domain ngoài làm proxy, chỉ nhận LAN IP `192.168.0.0/16`.
  * `Hard Gate #5`: Cấm chạy ADB trần thiếu `-s <serial>` hoặc chưa giữ device lock.
  * `ROLE_MODEL_MISMATCH`: Cấm dùng Claude Sonnet khi role là `worker`.

### C. Gate (Verification Checkpoint — Cổng nghiệm thu điều kiện)
- **Bản chất:** Không chỉ cấm đoán thụ động như Guard, Gate là **bước kiểm tra điều kiện cần và đủ để được đi tiếp hoặc chốt việc**.
- **Nhiệm vụ:** Muốn qua cổng thì phải có vé / bằng chứng thực tế đạt chuẩn:
  * `Canary Gate`: Phải test xanh trên 1 máy thật, có ảnh bằng chứng mới được mở rộng toàn farm.
  * `Closeout Gate`: Phải được Reviewer độc lập (Sol / Claude) chấm điểm $\ge 85/100$ mới được phép commit/push.
  * `Farm Network Gate`: Phải thỏa mãn $L2 \rightarrow L3 \rightarrow L4$ thì mới được coi là mạng thông.

👉 **Kết luận:** 3 khái niệm này tạo thành thế kiềng 3 chân hoàn chỉnh: **Hook** bắt không cho lọt lưới, **Guard** triệt tiêu hành vi phá hoại, **Gate** nghiệm thu chất lượng bàn giao.

---

## 2. Vì Sao Thư Mục Hook Hệ Thống Là Vùng Cấm Tuyệt Đối?

1. **Chống Agent Tự Ý Sửa Luật (Anti Self-Tampering):**
   - Nếu Coordinator/Worker được sửa Hook, mỗi khi bị chặn (bị chặn quét đĩa, bị chặn timeout...), phản xạ ngắn nhất của AI là nhảy vào xóa luôn dòng code của Guard để lệnh chạy qua.
   - Guard là "Trọng tài", cầu thủ không được phép sửa luật trọng tài.
2. **Bán Kính Sát Thương Toàn Hệ Thống (Blast Radius):**
   - Hook chạy trước từng tool call của mọi session, mọi subagent, mọi cronjob.
   - Sửa ẩu gây `SyntaxError` hoặc vòng lặp vô hạn trong Hook sẽ làm tê liệt toàn bộ Hermes Gateway.
3. **Phân Định Ranh Giới Quyền Lực:**
   - Operator (User) = Lập pháp (đặt ra Invariants & Hooks).
   - Agent = Hành pháp (thi công trong khuôn khổ luật).

### Khi nào sửa ở Wrapper vs Sửa ở Hook?
- **Tầng Wrapper (`claude_worker.py`, `dispatch_worker.py`):** Dành cho logic phân vai nghiệp vụ, validation tham số CLI, model restriction. An toàn, sửa sai chỉ hỏng lệnh đó, test offline được.
- **Tầng Hook (Bộ lọc shell/terminal toàn cục):** Dành cho ranh giới an toàn hệ điều hành toàn cục (quét đĩa, foreground timeout, bare ADB commands). Đụng vào cần sự giám sát chặt chẽ của Operator.

---

## 3. Quy Chuẩn Kiểm Tra Xung Đột 2 Tầng (Two-Tier Conflict Verification Protocol)

Từ nay, trước khi bất kỳ module Gate/Guard/Script mới nào được thiết kế hay sửa đổi, BẮT BUỘC phải đối soát qua 2 tầng:

### Tầng 1: Hạ Tầng Kỹ Thuật (System Guards)
1. **`guard_android_proxy.py`:** Giá trị `http_proxy` có đảm bảo là RFC1918 LAN IP (`192.168.110.2:<port>`) không? Có bị truyền domain URL nhầm không? Direct mode có dùng `:0` không?
2. **`guard_cronjob_safety.py`:** Mọi subprocess Windows có bọc `creationflags=0x08000000` (`CREATE_NO_WINDOW`) chống cướp focus desktop không?
3. **`Hard Gate #5`:** Mọi lệnh ADB có gắn cứng `-s <serial>` và bọc trong `operator_device_lock` không?
4. **Codebase Protection:** Có chứa hàm quét đĩa diện rộng (`os.walk`, `rglob`, `grep -r`) không? Có đụng chạm file guard nhạy cảm không?

### Tầng 2: Kỷ Luật Nghiệp Vụ Của Operator (User Invariants)
1. **Ngoại lệ Direct:** Đã xử lý các máy direct M67, M69 chưa (bỏ qua probe proxy)?
2. **Cứu máy khẩn cấp:** Đã hỗ trợ `force_preempt=True` trong `operator_device_lock` khi cứu máy kẹt chưa?
3. **Bảo vệ ca nuôi (Nurture Protection):** Có kiểm tra trạng thái hiện tại (`NOOP_HEALTHY`) trước khi ngắt mạng để tránh làm rớt 25 workers TikTok đang chạy không?
4. **Mạng Sing-box LAN:** Có tuyệt đối cấm VPN và ưu tiên cấu hình Ruijie > Aruba không?
5. **Kiểm thử Offline:** Toàn bộ test suite có chạy mock 100% offline dưới 30 giây không?

---

## 4. Khóa Cơ Học Trong `claude_worker.py` (Triệt Tiêu Bệnh Xin Lỗi Mồm)

Vá dứt điểm 3 lỗi lặp lại khi gọi Claude CLI:
1. **Chặn Đứng Role Model Mismatch:**
   ```python
   if role == "worker" and args.model and "sonnet" in args.model.lower():
       sys.exit("[ROLE_MODEL_MISMATCH] Role worker bị khóa cứng: CẤM TUYỆT ĐỐI dùng Sonnet làm worker! Phải dùng Haiku hoặc Agy CLI.")
   ```
2. **Khóa Van Fallback:** Haiku gặp lỗi/timeout -> 100% rẽ sang `ag_cli.py fix`, cấm nâng cấp lên Sonnet.
3. **Cảnh Báo Foreground Timeout:** Lệnh chạy lâu bắt buộc bọc `terminal(background=True, notify_on_complete=True, timeout=120..180)` để không văng `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` (>60s).
