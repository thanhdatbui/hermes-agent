# Desktop Performance Onset Reference

## Evidence matrix

| Question | Evidence to collect | Interpretation |
|---|---|---|
| When did it start? | User last-good/first-bad boundary | Primary filter for updates and events |
| Is it local or network? | Does picture/audio/input pause? RTT and packet loss | Network evidence alone does not prove local freeze |
| What changed? | Update history, app versions, updater logs, modified files | A recent change outranks a familiar long-running app |
| What runs at the freeze? | Per-second CPU/GPU/I/O/process restart samples | Snapshot load is only a suspect signal |
| Is hardware involved? | WHEA/Display/Disk events with timestamps | Repetition matters; causality still requires alignment |
| Can it be isolated? | One-variable A/B across multiple expected intervals | Controlled result is stronger than plausibility |

## Practical sequence

1. Record the symptom and last-known-good boundary.
2. Query System/Application/Defender/Task Scheduler events only from that boundary onward.
3. Record update/install times and relevant executable/log mtimes.
4. Reproduce with the game actually running; record freeze timestamps manually.
5. Sample CPU, GPU, disk queue/I/O, memory, network, and process restarts at 1-second intervals.
6. Join telemetry and events by timestamp with a small tolerance (for example ±2 seconds).
7. Rank only hypotheses that make a falsifiable prediction.
8. If needed, run one authorized A/B test and repeat long enough to cover 3–5 expected freeze intervals.

## Lessons from a representative Windows case

- A long-running overlay/booster may have worked for months; do not call it the cause solely because it is resource-heavy. Check whether it updated, restarted, changed cache/state, or aligns with the new symptom.
- A sudden morning onset can be more consistent with an automation crash/restart loop, a sync/security job, or a new service state than with a static incompatibility.
- Repeated `adb.exe` crashes are relevant to a farm workload, but they do not prove they caused a League freeze; require timestamp alignment or a controlled workload-off test.
- A corrected WHEA PCIe event is a hardware signal worth escalating, not an automatic explanation for every stutter.
- DCOM 10016 warnings are commonly noisy; do not elevate them without component/timestamp correlation.
- A DNS timeout may explain a network symptom, but not a full rendered-screen freeze unless the user reports only network behavior.
- If the game was not running during collection, the correct status is **game-specific correlation unproven**.

## Reporting language

Use:

- "Observed: ..."
- "Leading hypothesis: ..."
- "Not proven because: ..."
- "Next single-variable test: ..."

Avoid:

- "X definitely caused it" from a process list;
- "hardware failure" from one corrected WHEA event;
- "network issue" from DNS alone;
- "verified" when no live reproduction or A/B test was performed.
