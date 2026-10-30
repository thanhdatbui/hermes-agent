# Shared MAC Address Collision & PADO Drop on MT7530 DSA (Xiaomi R3G)

## Problem Signature
- `carrier = 1` on physical outer white port (`lan1`).
- Physical cable & ISP account (`hyn_gftth_tamnhb0`) verified working when plugged into separate hardware.
- On OpenWrt R3G, running `ifup wan` or `pppd` on `lan1` results in repeated:
  ```text
  Send PPPOE Discovery V1T1 PADI session 0x0 length 12
  Timeout waiting for PADO packets
  Unable to complete PPPoE Discovery
  Exit.
  ```
- Meanwhile, middle port (`lan2`) is actively running `WAN2` + 8 PPPoE MACVLAN sub-interfaces.

## Root Cause
1. **Identical HW MAC on DSA Switch Ports:**
   By default, the MT7530 DSA switch driver clones the SoC base MAC (e.g. `40:31:3c:03:84:54`) across all slave netdevs (`eth0`, `lan1`, `lan2`, `wan`).
2. **BRAS / Switch L2 Drop on Collision:**
   When `lan2` is actively connected to the Viettel BRAS (`TBH8001BRA01`) with MAC `40:31:3c:03:84:54`, issuing PADI frames from `lan1` with the EXACT SAME MAC causes:
   - The upstream BRAS or local MT7530 switch forwarding table to recognize the frame as an illegal MAC loop / duplicate session.
   - PADO packets are either dropped at the BRAS or misrouted/suppressed by the switch HW table before reaching the CPU DSA master `eth0`.

## Resolution & Verification Workflow
1. **Assign a Unique Locally Administered MAC Address to `lan1`:**
   In `/etc/config/network`:
   ```uci
   config device 'dev_lan1'
       option name 'lan1'
       option mtu '1500'
       option macaddr '02:11:22:33:44:10'

   config interface 'wan'
       option device 'lan1'
       option proto 'pppoe'
       option username 'hyn_gftth_tamnhb0'
       option password 'N5WU2A'
       option metric '200'
       option defaultroute '0'
       option peerdns '0'
   ```
2. **Verification with Claude CLI / tcpdump:**
   Immediately upon assigning MAC `02:11:22:33:44:10`, running `pppd` captures PADO in 11ms:
   ```text
   Send PPPOE Discovery V1T1 PADI session 0x0 length 12
   Recv PPPOE Discovery V1T1 PADO from F4:CC:55:8C:C8:84 (TBH8001BRA01)
   Send PPPOE Discovery V1T1 PADR
   Recv PPPOE Discovery V1T1 PADS
   PAP authentication succeeded
   ```
3. **Sub-Interfaces on Line 0 (`lan1`):**
   All subsequent MACVLAN interfaces on `lan1` (`mvl11..mvl17`) must also use distinct MACs (`02:11:22:33:44:11..17`) to allow 8 concurrent PPPoE sessions across the second fiber line.
