# Network Gate Contract — M7 Incident Lessons

## Incident pattern

A machine in the first Wi-Fi group was given a neighboring group’s PSK by an ad-hoc recovery flow. The AP logged an encrypted-message integrity/MIC authentication failure; Android then reported association rejection and left the supplicant disconnected. The important lesson is not the particular password: it is that a caller was allowed to supply network identity and credential independently of the machine mapping.

## Evidence chain to preserve

- Canonical machine-to-Wi-Fi profile mapping, including group ranges.
- Independent machine-to-serial provenance.
- AP authentication reason and Android supplicant state.
- Current SSID/BSSID, IPv4, route, gateway reachability.
- Resolved proxy endpoint and proxy-layer verdict.
- Sanitized profile hash and timestamps.

Never store or repeat the PSK in reports, command-line examples, screenshots, or error text. Use a profile ID/fingerprint instead.

## Acceptance contract

`apply_profile(machine)` is the only mutation entrypoint. It must:

1. Validate and hash the SSOT.
2. Resolve exactly one profile and one serial.
3. Acquire the device lock.
4. Read current state and return `NO_OP` if all layers are healthy.
5. Apply only the resolved profile.
6. Verify L2 before L3, and L3 before L4.
7. Stop on the first mismatch with `FINAL_BLOCKED`.
8. Write sanitized evidence and release the lock.

A single canary proves only that canary. It does not prove a whole group or farm is clean.

## Legacy Android note

Older Samsung Android versions may not expose modern `cmd wifi` subcommands. Device-specific join/removal mechanics belong inside the canonical primitive, must be explicitly quoted for SSIDs containing spaces, and must be followed by independent readback. Do not let a compatibility workaround become a new ad-hoc caller path.

## Review decision

The agreed architecture is: SSOT and validated O(1) resolver; caller passes machine only; lock before mutation; idempotent read-before-write; one-way L2/L3/L4 gates; fail-closed on credential/auth/readback mismatch; sanitized evidence; idle canary per group; staged rollout; offline mocked tests for every fail-closed branch.
