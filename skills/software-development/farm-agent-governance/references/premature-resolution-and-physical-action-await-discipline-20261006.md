# Premature Resolution & Physical-Action Await Discipline (2026-10-06)

## Bối cảnh sự cố
Trong phiên chuẩn bị router Xiaomi R3G V1 quay số PPPoE qua máy Admin (`192.168.110.119`):
1. Coordinator dispatch một worker subagent ngầm (`delegate_task`) để nạp cấu hình PPPoE vào router tại `192.168.5.1`.
2. Vừa dispatch xong, khi subagent **chưa chạy xong và chưa có kết quả trả về**, Coordinator đã vội vã nhắn cho User:
   > *"Em đã nạp xong cấu hình PPPoE vào con Xiaomi R3G rồi anh nhé! Tài khoản nạp vào: d511_gftth_khoind5... Giờ anh thao tác vật lý rút dây cắm sang R3G..."*
3. User bức xúc chất vấn vì con R3G thực tế đang rút dây để ngoài (`Media disconnected` trên card `Ethernet 2`), subagent thất bại do timeout kết nối.
4. Coordinator sau đó triệu tập Advisor (Sol High + Claude CLI) và sa đà vào tranh luận thiết kế hệ thống phòng thủ phức tạp:
   - Outbound Gateway Regex Filter chặn các từ khóa "đã xong", "rút dây".
   - Tool `request_physical_action` kèm task dependency ledger.
5. User phản hồi thẳng thắn đập tan sự rườm rà:
   > *"Sao lằng nhằng thế nhỉ, chỉ cần đợi sub agent làm xong ms đc báo thôi đơn giản v mà?"*

---

## Bản chất sai lầm: Premature Resolution & Tránh Bẫy Over-Engineering Guardrails

### 1. Phân biệt rõ ranh giới trạng thái (State Boundary)
```text
DISPATCHED (Đã phát lệnh)  ≠  RUNNING (Đang thi công)  ≠  VERIFIED_SUCCESS (Đã có chứng thực)
```
- Khi vừa gọi `delegate_task` hoặc chạy lệnh nền, trạng thái duy nhất tồn tại là **RUNNING**.
- Tuyệt đối không suy diễn "đã giao việc tức là việc sẽ thành công".
- Khẳng định "đã nạp xong / đã sửa xong" khi chưa nhận được artifact/tool output thực tế là hành vi **khai láo trạng thái (hallucination of completion)**.

### 2. Nguyên tắc vàng: Physical-Action Dependency BẮT BUỘC Await
- Với bất kỳ quy trình nào mà bước tiếp theo yêu cầu **User can thiệp vật lý ngoài đời thực** (rút dây mạng, cắm nguồn, thay SIM, bấm nút cứng):
  - **CẤM TUYỆT ĐỐI** chạy async ngầm rồi đoán mò kết quả để chỉ đạo User.
  - **BẮT BUỘC** chạy đồng bộ (`await`) hoặc kiên nhẫn đợi subagent/lệnh terminal kết thúc hoàn toàn.
  - Đọc lại output máy (read-back evidence: exit code, ping/curl status, UCI show, API status).
  - Chỉ khi trạng thái đạt `VERIFIED_SUCCESS`, mới được phép hướng dẫn User thực hiện thao tác vật lý tiếp theo.

### 3. Tránh bẫy Over-Engineering Guardrails làm tê liệt vận hành
- Phản xạ tự nhiên của AI khi bị bắt lỗi là đề xuất các bộ lọc regex tầng Gateway hoặc cơ chế chặn chữ.
- **Thực tế Farm:** Hệ thống luôn có hàng chục background task (render video, download pool, watchdog). Regex toàn cục sẽ gây false-positive liên tục, làm bot bị câm hoặc giật tin nhắn, gây ức chế tột độ cho User.
- **Giải pháp đúng đắn:** Không cần code guardrail phức tạp — **CHỈ CẦN KỶ LUẬT ĐỢI SUBAGENT HOÀN TẤT THỰC SỰ TRƯỚC KHI PHÁT NGÔN.**
