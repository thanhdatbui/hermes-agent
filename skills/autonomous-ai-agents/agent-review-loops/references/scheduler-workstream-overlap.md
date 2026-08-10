# Scheduler workstream overlap checklist

Use this before dispatching or continuing any scheduler/orchestration implementation.

## 1. Classify the goal

Write one sentence for each active goal:

- **Schedule product:** random per-account picker, runner, feed/post policy, cadence and slot constraints.
- **Core harness:** manifest, journal, transition matrix, recovery, proof/replay, lock and notification contracts.
- **Hermes runtime:** cron job creation, launcher, cadence, delivery and live enablement.

These can be dependencies, but they are not automatically separate products.

## 2. Discover parallel work

Search recent sessions and delegation artifacts for:

- `schedule`, `random`, `picker`, `runner`, `watcher`
- `Hermes cron`, `feed_then_post`, `manifest`
- repository paths and current branch

Inspect the latest goal and acceptance criteria, not only the latest worker result. A worker result can be stale or belong to another layer.

## 3. Check runtime separately

List current cron jobs and live processes. Report two independent facts:

- **Code/ownership overlap:** two workstreams build or modify the same scheduler contract/files.
- **Runtime overlap:** two enabled jobs/processes can actually launch the same farm action.

“No farm cron is enabled” only disproves runtime duplication; it does not disprove code/architecture duplication.

## 4. Establish ownership

If two goals both create `picker`, `runner`, `watcher`, `manifest`, or `feed_then_post`:

1. Choose one schedule-product owner.
2. Make the core harness a shared dependency only if that owner accepts its contract.
3. Stop or pause the duplicate implementation stream.
4. Do not create a second scheduler with a different manifest/state machine.
5. Record the ownership decision in the coordinator checkpoint or handoff artifact.

## 5. Safe response format

Use concise Vietnamese:

- `Trùng mục đích` — same schedule product/contract or same files.
- `Chưa trùng runtime` — no duplicate live cron/process currently enabled.
- `Hướng xử lý` — owner, merge/dependency decision, and what must stop.

Do not claim the core harness is an independent product when it is actually the implementation substrate for the schedule product. Do not continue audit rounds solely because tests are green if ownership has not been reconciled.
