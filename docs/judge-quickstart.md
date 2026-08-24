# Judge quickstart

## 1. Prove the live boundary

With the API, dashboard, and Protegrity Compose stack running:

```text
.venv\Scripts\python.exe scripts\demo-preflight.py
```

The command fails unless the isolated gateway is real Protegrity, real-mode fallback is disabled, the API process has no Protegrity credentials, NVIDIA is configured, a synthetic identifier is protected, raw canaries are absent, all eight attacks are registered, a live injection is blocked, and the evidence chain verifies. It never prints credentials or protected values.

## 2. Show working protection

Open [http://localhost:3001/protection](http://localhost:3001/protection) and run the synthetic example. Verify the before/after view removes the name, email, account ID, and debug secret; provider is `protegrity`; postcondition is zero raw matches; and a SHA-256 fingerprint is present. Open the linked receipt.

## 3. Show a realistic attack

Open [http://localhost:3001/attack-lab](http://localhost:3001/attack-lab), choose `LPA-01`, and run it. Verify it is blocked at `semantic guardrail` by Protegrity. Repeat with the log-injection, encoded-exfiltration, or malicious-MR scenario, then open its trace.

Before the attack, open [http://localhost:3001/ai-review](http://localhost:3001/ai-review) and run the synthetic engineering decision. This executes the complete working Protegrity → NVIDIA → output-scan pipeline. Open its receipt and inspect `DESTINATION_SCANNED` for the exact serialized provider payload's SHA-256 and byte count.

## 4. Show complete pipeline evidence

Open [http://localhost:3001](http://localhost:3001). The Privacy Control Center proves gateway isolation, fail-closed status, Protegrity + NVIDIA readiness, stage-by-stage receipts, and live hash-chain integrity. A model trace includes `DESTINATION_SCANNED` with the exact protected provider payload's hash and byte count but never its contents.

## 5. Reproduce automated checks

```text
.venv\Scripts\python.exe -m pytest legacy\tests -q
.venv\Scripts\python.exe -m pytest lore-cli\tests -q
cd lore-dashboard
npm run lint
npm run build
```
