# Ethernet Link-OK But RX-Zero & PPPoE LCP Lowerdown Triage (2026-10-09)

## 1. Hiện tượng & Phản xạ Operator
- **Hiện tượng:** Toàn bộ các kết nối PPPoE trên router (MikroTik) đồng loạt rớt mạng (`status: disconnected`, `0/60 running`), nhật ký debug ghi nhận liên tục `LCP lowerdown` / `LCP down event in starting state`.
- **Phản ứng tự nhiên của Operator:** Nhìn mắt thường vào cổng router thấy đèn LED vẫn sáng xanh, dây cáp mạng vẫn cắm chặt vào cổng WAN và modem/converter nên phản hồi: *"Ủa tao thấy vẫn cắm bình thường mà, kiểm tra lại coi"*.

---

## 2. Bản chất kỹ thuật & Cạm bẫy "Link-OK"
- **Đèn cổng sáng (`status: link-ok, rate: 1Gbps`):**
  - Chỉ chứng minh tầng vật lý PHY giữa 2 chip mạng (NIC) có tín hiệu điện áp/xung nhịp (Auto-Negotiation hoàn tất).
  - Hoàn toàn KHÔNG chứng minh thiết bị đầu bên kia (modem/converter/ONT) đang truyền dữ liệu ở tầng Layer 2 (Data Link) hay tầng quang (WAN).
- **Lý do dẫn tới `RX = 0` dù cáp vẫn cắm:**
  1. **Modem/Converter FPT bị mất tín hiệu quang (LOS / PON đỏ):** Cổng LAN của converter vẫn cấp nguồn điện nên đèn link MikroTik sáng, nhưng không có tín hiệu quang từ đài trạm FPT để chuyển tiếp gói tin $\to$ RX trả về MikroTik là 0 bytes.
  2. **Treo phần cứng chip switch/CPU của Modem (Hardware Freeze):** Cục modem bị đơ controller, ngừng forward frames qua cổng LAN dù PHY vẫn duy trì điện áp.
  3. **Cáp đứt ngầm 1 chiều (Unidirectional link):** Cặp dây TX truyền đi được nhưng cặp dây RX bị đứt hoặc tiếp xúc kém ở đầu bấm hạt mạng RJ45.

---

## 3. Quy trình chẩn đoán O(1) bằng Bắt Gói & Đo Lưu Lượng (Evidence Matrix)

Không suy diễn suông, sử dụng 2 bước đo đạc kỹ thuật tức thì trên RouterOS API (`192.168.110.2:9090`):

### Bước 1: Đo biến thiên RX vs TX qua 2 giây
```python
t1 = api_call("/interface/ethernet?name=WAN1")
rx1, tx1 = int(t1[0]["rx-bytes"]), int(t1[0]["tx-bytes"])
time.sleep(2)
t2 = api_call("/interface/ethernet?name=WAN1")
rx2, tx2 = int(t2[0]["rx-bytes"]), int(t2[0]["tx-bytes"])
rx_delta = rx2 - rx1
tx_delta = tx2 - tx1
# Hiện trường lỗi: tx_delta > 0 (bắn PADI), rx_delta == 0 (0 byte nhận về)
```

### Bước 2: Bắt gói tin thực tế bằng `/tool/sniffer` trong 3 giây
```python
api_call("/tool/sniffer/stop", method="POST")
api_call("/tool/sniffer/set", method="POST", data={"interface": "WAN1", "memory-limit": "100"})
api_call("/tool/sniffer/start", method="POST")
time.sleep(3)
api_call("/tool/sniffer/stop", method="POST")
packets = api_call("/tool/sniffer/packet")
# Bằng chứng đanh thép: 100% packets là 'direction: tx', 0 packet 'direction: rx'.
```

---

## 4. Hướng dẫn Operator xử lý dứt điểm
1. **Kiểm tra đèn quang trên cục converter/modem FPT:**
   - Đèn `PON` có sáng xanh đứng yên không?
   - Đèn `LOS` có nhấp nháy đỏ không? (Nếu LOS đỏ: đứt cáp quang từ nhà mạng FPT ngoài đường).
2. **Reboot cứng modem FPT:** Rút nguồn điện cục converter FPT ra chờ 10 giây rồi cắm lại để xả treo chip switch.
3. **Cắm lại cáp LAN:** Rút dây cáp nối giữa cổng LAN modem FPT và cổng WAN MikroTik ra cắm lại thật chặt.
