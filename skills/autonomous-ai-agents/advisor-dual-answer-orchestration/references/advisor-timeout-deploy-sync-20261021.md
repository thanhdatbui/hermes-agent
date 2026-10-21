# Dong Bo Timeout Advisor Sol Da Tang Va Khoi Dong Lai Daemon (2026-10-21)

## 1. Hien tuong thuc te
Du da nang timeout cho Advisor Sol tu 45s len Idle Streaming Timeout (first-token 80s, idle 20s, max 140s, timeout_sec 150s), nhung sang phien moi van bi loi wall-clock deadline exceeded >45.0s.

## 2. Nguyen nhan cot loi
1. Da ban sao script (Multiple Script Replicas): Co 4 ban sao doc lap cua advisor_consult tren may:
   - Thu muc AppData skills
   - Thu muc D:/Taadaa/Hermes/skills
   - Thu muc D:/Taadaa/Hermes/deploy/hermes-home/skills
   - Thu muc D:/Taadaa/tools/consult_advisor.py
   Cac phien truoc chi sua 3 noi, bo quen thu muc deploy dan toi nap phai ban 45s cu.
2. RAM Cache cua Daemon Gateway: Tien trinh daemon giu nguyen module trong RAM tu luc boot 05:30 sang. Sua file tren dia chua co hieu luc neu chua khoi dong lai daemon.

## 3. Quy trinh dong bo
- Luon dong bo du ca 4 thu muc tren.
- Xoa sach file cache .pyc cu trong __pycache__.
- Khoi dong lai daemon gateway qua watcher khi he thong nhan roi.
