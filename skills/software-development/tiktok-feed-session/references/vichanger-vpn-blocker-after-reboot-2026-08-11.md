# ViChanger VPN blocker sau reboot — máy 78 (2026-08-11)

Chuỗi chẩn đoán + evidence khi `blocked-vichanger-vpn` vẫn còn sau 2 reboot.
Máy 78, serial `ce0916090a9d320a01`, SM-G930F. Batch lướt 15 máy ngẫu nhiên (artifact `.ai-runs/20260811-063050`).

## Chuỗi sự kiện

1. **Batch 1:** `blocked-vichanger-vpn` — `required Android VPN is not connected: interface=tun0 tun_up=False vpn_connected=False error=Device "tun0" does not exist.` (M5, M78 cùng lỗi; M62 lỗi khác = ADB transport).
2. 3-bước fix (B1+B2+B3 reboot) cả 3 máy → rerun (`20260811-071346`): M5 ✅ 30 swipes, M62 ✅ 24 swipes, **M78 vẫn fail VPN**.
3. 3-bước lần 2 (turn mới, budget B2/B3 đủ): reboot → `sys.boot_completed`=1, unlock, nhưng:
   - `ip addr show tun0` → `Device "tun0" does not exist.`
   - `ps -A | grep -i vichanger` → **RỖNG** = ViChanger KHÔNG auto-start sau boot.
4. Launch tay: `monkey -p vn.vichanger.app -c android.intent.category.LAUNCHER 1` → process lên (pid 13743) nhưng tun0 vẫn chưa có.
5. `dumpsys window | grep mCurrentFocus` → `Window{... com.android.vpndialogs/com.android.vpndialogs.ConfirmDialog}` = **Android VPN confirm dialog chặn connect**.

## Dialog evidence (uiautomator dump, 5625 bytes)

```
'Yêu cầu kết nối' | click: false | android:id/alertTitle
'Vi Changer muốn thiết lập kết nối VPN c' | click: false | com.android.vpndialogs:id/warning
'THOÁT' | click: true | android:id/button2 | [1099,844][1308,988]
'OK'   | click: true | android:id/button1 | [1308,844][1500,988]   <- center (1404,916)
```

Tap OK → dialog dismiss → focus `vn.vichanger.app/vn.vichanger.app.GUI.LoginActivity`.

## Dialog thứ 2 — "No LSPosed access !!!"

```
'Message' | click: false
'No LSPosed access !!!' | click: false
'OK' | click: true | [1308,655][1500,799]   <- center (1404,727)
```

Tap OK → vẫn LoginActivity, tun0 vẫn không tồn tại.

## Kết luận

**ViChanger bị LOGOUT** (mất phiên login) → không thể kết nối VPN → preflight fail mãi.
Block thật cần tay: login ViChanger (cần credentials của máy đó) hoặc kiểm tra app.
Báo MANUAL + screenshot evidence (`m78_vichanger_login.png`), KHÔNG tự đoán login,
KHÔNG reboot tiếp (B2/B3 hết budget turn). Lock máy giữ stale chờ user duyệt gỡ.

## Bài học áp dụng chung

- **Reboot KHÔNG đảm bảo ViChanger auto-start + VPN lên** — check `ps -A | grep vichanger` + `ip addr show tun0` sau boot; thiếu → launch bằng monkey.
- **VPN confirm dialog LÀ benign system dialog** (cho phép connect) — tap OK (`android:id/button1`) được phép; KHÔNG thuộc nhóm sensitive login/OTP/2FA. Cùng class "No LSPosed access" warning → OK.
- **`LoginActivity` = mất phiên login** → VPN watcher (gan-proxy) không thể cứu; đừng lặp reboot.
- **Verify hồi phục sau reboot đừng dựa vào `uiautomator dump` byte count**: loop `dump >/dev/null 2>&1; exec-out cat | wc -c` trả 0 nhiều lần dù máy boot xong (dump fail bị nuốt bởi redirect; uiautomator chưa ready). Chạy dump KHÔNG redirect → stdout `UI hierchary dumped to: /sdcard/check.xml` + `ls -la` (31KB) mới là chuẩn; vẫn 0 → B1 ATX-kill rồi thử lại.
- `mCurrentFocus` = `com.sec.android.app.launcher/...LauncherActivity` + `sys.boot_completed`=1 = máy đã hồi phục, đủ điều kiện relaunch (runner có `--prepare-tiktok` + ladder tự lo phần còn lại).
