# Protegrity Developer Edition feedback

Developer Edition made privacy an executable AI boundary instead of a masking feature added after inference. Separating Data Discovery, reversible protection, and Semantic Guardrails let LORE fail closed and produce receipts showing what ran without recording sensitive payloads.

The main integration friction was distinguishing hosted protection credentials from local Data Discovery and Semantic Guardrail services, plus understanding exact endpoint and authentication formats. A single version-pinned Compose reference showing discovery, protect/unprotect, input/output guardrails, health checks, outage behavior, and payload-safe logging would reduce setup time. We would also value a standard protection-receipt schema and more examples for pseudonymized RAG, source-code review, and purpose-scoped agent tools.

The strongest design lesson was not to equate “no entity detected” with “not sensitive.” LORE protects the full canonical payload, creates a separate minimized AI-safe representation, and rescans that representation before release.
