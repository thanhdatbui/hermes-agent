---
name: network-device-ap-conversion
description: |
  Provides a structured workflow for configuring a network device (typically a router)
  into an Access Point (AP) mode, either by using a dedicated AP mode setting or
  by manually disabling router functionalities (DHCP, NAT) and setting a static IP.

  This skill also covers troubleshooting common issues encountered during this process,
  such as login difficulties, hidden UI elements, and IP address conflicts.
version: 1.0.0
---
# Network Device to Access Point Conversion Workflow

This skill outlines the process of converting a consumer-grade router into an Access Point (AP) to extend Wi-Fi coverage within an existing network.

## Goal

To configure a secondary network device (the target device) to act as an Access Point (AP) within a primary network, sharing the primary network's subnet, DHCP services (from the primary router), and Wi-Fi SSID (optional).

## Prerequisites

1.  **Primary Router:** An existing main router (e.g., Ruijie) handling NAT, DHCP, and Internet access.
2.  **Target Device:** The device to be converted to an AP (e.g., ZTE H196A).
3.  **Login Credentials:** Administrative username and password for the target device.
4.  **Network Information:**
    *   Primary router's LAN IP address (and thus the network's gateway, e.g., `192.168.110.1`).
    *   Primary network's subnet mask (e.g., `255.255.255.0`).
    *   Desired Wi-Fi SSID and password for the AP (to match existing Wi-Fi, if applicable).
5.  **Physical Connection:** Target device is connected to the network, initially via its WAN port to a LAN port of the primary router for initial configuration (this will be changed later).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
