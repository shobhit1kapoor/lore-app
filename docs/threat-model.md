# LORE threat model

## Protected assets

- source-code diffs and unreleased product plans;
- issue and merge-request descriptions and comments;
- developer identities, email addresses, IP addresses, account and tenant identifiers;
- API keys, access tokens, debug tokens, credentials, and secrets accidentally pasted into engineering work;
- organizational decisions, rejected alternatives, incident history, and security precedents;
- system prompts, memory-bank content, model requests/responses, and agent-tool output;
- Protegrity, NVIDIA, GitLab, and GitHub credentials.

## Primary threats and controls

| Threat | Control | Evidence |
|---|---|---|
| Direct or indirect prompt injection | Protegrity input Semantic Guardrails plus deterministic injection checks | blocked trace and processor outcome |
| Secret or identity reaches the model | discovery, pseudonymization/masking, complete-prompt postcondition | provider payload hash/bytes and zero-match counts |
| Output reveals protected memory | output `pii` guardrail, discovery, canary scan, protected release | output policy event and receipt |
| Cross-project memory/tool access | project-scoped adapters and explicit destination context | tool event with project/resource metadata |
| Raw memory persists in wiki/repository | pre-write protection and repeated output boundary | memory-write receipt |
| Log injection or accidental payload logging | structured allowlisted telemetry and sensitive-key redaction | hash-chained payload-free event |
| Privacy service outage causes unsafe fallback | real-mode `PROTEGRITY_FAIL_CLOSED=true` | `PROTECTION_FAILED` event and no downstream call |
| Credential theft from API/model worker | credentials live only in the isolated gateway `.env` | readiness reports credential isolation |
| Evidence tampering | append-only SHA-256 chain | live chain-verification result |

## Residual risk

Pseudonymized engineering facts can remain commercially sensitive. They still require transport encryption, repository authorization, purpose limitation, retention controls, and independent production security review. Classifiers and LLMs are probabilistic, so LORE layers deterministic secret patterns, scoped tools, postconditions, and canaries around Protegrity rather than treating one model as infallible.
