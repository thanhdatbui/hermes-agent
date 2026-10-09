# Validated rogue-SSID canary pattern

## Evidence pattern

On an Android 8 farm handset, `cmd wifi` returned no implementation. A locked `dumpsys wifi` showed the current record with a rogue SSID and a concrete `Net ID`. The historical `rec[...]` list also contained old SSID events, so it was not used as the source of the ID.

## Validated operation

With the current Net ID only:

```text
adb shell service call wifi 14 i32 <CURRENT_ROGUE_NET_ID>
```

The canary returned a Parcel boolean containing `00000001`. Immediate readback showed the rogue network was no longer the active `mWifiInfo` network. A configured-network readback through Wi-Fi service transaction 4 no longer contained the rogue SSID. The device was then rejoined to its mapped farm SSID with `adb-join-wifi`; readback reached `Supplicant state: COMPLETED` and a `192.168.110.x` address.

## Important limitation

This validates removal of an *active* rogue profile. It does not prove that a saved rogue profile can be safely identified on a device that is currently on a different SSID. Do not generalize the canary by taking a stale event-history `nid` or by trying every network ID. Build and test a reliable configured-network parser first, or leave that device untouched with evidence.

## Reporting

Report counts from per-device artifacts, not from the launcher exit code. Distinguish `NO_DAT_EVIDENCE`, successful removal with online farm readback, removal requiring follow-up, lock timeout, and command error. Never include Wi-Fi passwords, tokens, or full credential arguments in the report.
