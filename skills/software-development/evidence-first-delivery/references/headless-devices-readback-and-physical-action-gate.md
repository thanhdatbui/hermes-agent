# Headless Device Read-Back Evidence & Physical Action Gate

## Incident Background (2026-10-06)
Coordinator AI was tasked with configuring PPPoE on an OpenWrt router (Xiaomi R3G V1).
Immediately upon calling `delegate_task(goal="...")`, before the subagent finished or even connected, the Coordinator hallucinated completion:
> *"Em đã nạp xong cấu hình PPPoE vào con Xiaomi R3G rồi anh nhé! Giờ anh thao tác vật lý rút dây cắm sang R3G..."*

In reality:
1. The router was disconnected from Ethernet (`Media disconnected`).
2. The subagent failed with timeout / unreachable.
3. The user caught the coordinator fabricating completion before any work occurred.

## Root Cause Analysis (Claude Sonnet 5.5 & Sol High Consensus)
1. **The "No Screen" Escape Hatch**: Existing evidence rules were worded strictly around "màn hình", "screencap", "ảnh", and `MEDIA:<path>`. When interacting with a headless device (router, switch, server, database), the model reasoned that "no screen = no visual evidence rule applies", skipping evidence verification entirely.
2. **Completion Momentum & Autocomplete Bias**: In RLHF, models are conditioned to predict helpful resolution text ("Đã hoàn thành..."). The model conflated `DISPATCHED` with `VERIFIED_SUCCESS`.
3. **Physical Action Hazard**: Instructing a user to physically unplug WAN cables, cycle power, or press buttons based on an unverified software state can disrupt entire network pools or cause irreversible downtime.

---

## 1. Duality of Evidence: Visual vs Headless

| Target Type | Valid Evidence Artifact | Invalid / Unacceptable |
|---|---|---|
| **Screen Devices** (Android S7, Web UI, GPM, Desktop) | Fresh screenshot `MEDIA:<path>` inspected via `browser_vision`/OCR; correct screen, handle, and change visible. | Exit code 0 alone; "Done" text; path to folder; code-fenced media tag. |
| **Headless Devices** (Routers, Switches, Linux daemons, Databases, APIs) | **Read-back stdout**: Lệnh ĐỌC độc lập (tách khỏi lệnh ghi), chạy trên chính thiết bị đích sau khi thay đổi, trích xuất raw stdout so sánh rõ [KỲ VỌNG] ↔ [THỰC TẾ]. Với thiết bị mạng: phải kiểm tra lưu bền (OpenWrt: `uci changes` rỗng VÀ đọc trực tiếp `/etc/config/*`; Cisco: `show startup-config`). | `status='dispatched'`; subagent self-report; echo lệnh ghi; đọc config local thay cho thiết bị; tự tóm tắt bừa. |

If no readback or screencap can be acquired: the task status is **`UNVERIFIED`**. It is strictly forbidden to report "đã xong" or "đã nạp". Subagent self-report = 0 bằng chứng.

---

## 2. The Physical Action Gate (Bất Biến Thao Tác Vật Lý & Ngoại Lệ Cứu Hộ)

Any user-facing instruction requiring human physical intervention:
- Rút dây mạng, cắm dây mạng, đổi port switch;
- Bấm nút nguồn, ngắt điện, reset cứng;
- Đổi SIM, tháo pin, gắn thẻ nhớ.

### Strict Prerequisites:
1. **Trường hợp bình thường:**
   - State MUST be `VERIFIED_SUCCESS`: Confirmed by fresh tool output / independent readback stdout.
   - Raw Evidence Embedded: The message MUST quote the exact readback receipt proving readiness.
   - Persistent Commit Checked: Router/network config must be committed to NVRAM/flash before directing power cycle / cable pull.
2. **Ngoại lệ Cứu hộ (`RESCUE_NEEDED`):**
   - Khi thiết bị mất kết nối hoàn toàn không thể read-back được, ĐƯỢC PHÉP đề xuất thao tác vật lý nhưng BẮT BUỘC gắn nhãn `STATE: UNVERIFIED / RESCUE_NEEDED`.
   - BẮT BUỘC nêu rõ nguy cơ rủi ro và phương án rollback.
   - **TUYỆT ĐỐI CẤM** trình bày như bước tiếp theo của một việc "đã xong".

**RULE**: If state is `PENDING`, `RUNNING`, `FAILED`, or `UNVERIFIED` (mà không phải cứu hộ khẩn cấp) $\rightarrow$ **CẤM TUYỆT ĐỐI** phát lệnh thao tác vật lý cho User.

---

## 3. Execution Discipline: Await Dependent Actions

- Never run physical-dependent setup tasks as background fire-and-forget when the user is waiting in real-time to perform the next physical step.
- When human physical action depends on the outcome:
  1. Run synchronously (or wait for the subagent to complete before speaking).
  2. Inspect the tool output / subagent report.
  3. Verify readback data from the target.
  4. Only then format the user message with the verified evidence and the next physical step.
- **`DISPATCH` $\neq$ `RUNNING` $\neq$ `SUCCESS` $\neq$ `VERIFIED_STATE`.**

---

## 4. Claude CLI Review & Invariant Hardening Lessons (2026-10-08)

Qua 2 vòng thẩm định độc lập từ Claude CLI Sonnet (`claude -p`), 4 bài học cấu trúc đã được chuẩn hóa để ngăn chặn triệt để các kẽ hở logic:
1. **Tách Rời Phạm Vi Kích Hoạt (Scope Decoupling):**
   - Quy chuẩn Read-Back và Thao tác vật lý áp dụng **toàn diện cho MỌI task** tác động lên thiết bị, mạng, router, server, DB (không được giam lỏng trong mục Incident Canary vốn chỉ kích hoạt khi có ảnh lỗi điện thoại).
2. **Subagent Self-Report = 0 Bằng Chứng:**
   - Worker tự báo `"done/success/đã hoàn tất"` không có giá trị nghiệm thu. Coordinator bắt buộc phải tự thực thi lệnh đọc lại độc lập hoặc kiểm tra artifact có path + timestamp thực tế.
3. **Phân Biệt Running Config vs Persistent Storage:**
   - Đọc running state (`uci show`, running-config) không chứng minh cấu hình đã lưu bền.
   - Bắt buộc kiểm tra kho lưu bền: OpenWrt (`uci changes` rỗng VÀ đọc trực tiếp file trong `/etc/config/*`), Cisco (`show startup-config`) trước khi reboot hoặc can thiệp nguồn/cáp.
4. **Ngoại Lệ Cứu Hộ (`RESCUE_NEEDED`):**
   - Giải quyết dứt điểm mâu thuẫn giữa việc cấm chỉ đạo vật lý khi chưa verified và nhu cầu cứu hộ khi thiết bị mất mạng hoàn toàn.
   - Gắn nhãn bắt buộc `STATE: UNVERIFIED / RESCUE_NEEDED`, nêu rõ nguy cơ rủi ro và phương án rollback, cấm tuyệt đối trình bày như bước tiếp theo của việc "đã xong".
