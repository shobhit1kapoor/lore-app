# LORE 10–15 minute demo script

## 0:00–1:00 — What LORE is

Open the Privacy Control Center. Explain that LORE is living organizational memory: it follows engineering work from issue to production, predicts repeated failures, checks merge requests against past decisions and developer promises, catches security regressions, and preserves the reasoning behind the code.

State the privacy problem: issues, diffs, review comments, identities, secrets, incident history, and strategic decisions are valuable AI context but unsafe to send raw to models, tools, memory, or logs.

## 1:00–3:00 — Technical design

Use the eight-stage live pipeline on the overview:

1. project and purpose authorization;
2. Protegrity Data Discovery;
3. canonical protection and pseudonymization;
4. input Semantic Guardrails;
5. scoped retrieval;
6. minimum-necessary NVIDIA and tools;
7. output leak/canary scan;
8. hash-chained Protection Receipt.

Point out that only the Privacy Gateway has Protegrity credentials. The API readiness card proves the application process has none. Explain fail-closed behavior: no protection proof means no write or model call.

## 3:00–5:00 — Working protection

Open Protection Lab and run the synthetic example. Show that the name, email, account ID, and debug token disappear from the AI-safe view while the engineering instruction remains useful. Point out:

- provider `protegrity`;
- detected categories;
- zero raw matches after protection;
- payload fingerprint;
- link to the receipt.

Open the receipt and show discovery, tokenization/masking, protection, policy outcome, and payload-free metadata.

## 5:00–7:30 — Realistic AI pipeline

Explain how an actual MR enters through a verified webhook. LORE retrieves project-scoped decisions and diffs, protects the complete prompt, runs input guardrails, then sends the minimum-necessary protected request through the NVIDIA adapter.

In a model trace, show `DESTINATION_SCANNED`: the SHA-256 and byte count describe the exact serialized request; the contents and credentials are never logged. Explain that returned content passes output `pii` guardrails and discovery before it can become a comment or memory.

## 7:30–10:00 — Attack Lab

Open Attack Lab and briefly show the eight categories. Run `LPA-01`; show it blocked at Protegrity Semantic Guardrails. Then select log injection or encoded exfiltration to demonstrate a different boundary. Open the linked receipt.

Explain that an attack is useful only if the system proves where it was stopped. LORE ties the scenario, trace, boundary, provider decision, and evidence chain together.

## 10:00–12:00 — Product implementation

Show Protected Memory and explain the lifecycle:

- SpecForge predicts failure before code exists;
- Guardkeeper performs five-layer MR review;
- Lorekeeper extracts decisions from discussion and code;
- intentional overrides evolve memory rather than deleting history;
- Lorecast and onboarding convert protected memory into actionable team context.

Emphasize that Protegrity is central to all modes because they share one protection and model gateway.

## 12:00–13:30 — Evidence and verification

Return to the overview. Show gateway isolation, Protegrity + NVIDIA readiness, blocked operations, and verified hash-chain count.

Run `.venv\Scripts\python.exe scripts\demo-preflight.py`. Explain each passing gate without showing any `.env` file. Mention the automated result: 17 privacy/API/agent tests, 43 CLI tests, TypeScript validation, and production build all pass.

## 13:30–14:00 — Close

Summarize: LORE makes organizational history useful to AI without treating raw engineering data as acceptable model input. Protegrity controls what crosses each boundary, NVIDIA performs replaceable reasoning, and receipts make the promise verifiable.

State that all demonstration data is synthetic and that LORE makes no production-security or compliance claim.
