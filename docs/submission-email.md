# Submission email

**To:** hackathons@protegrity.com  
**Subject:** AI Pipeline Security Challenge Submission — LORE

Hello Protegrity Hackathon Team,

Please find our submission for the AI Pipeline Security Challenge: **LORE — Protected Organizational Memory for Software Teams**.

## GitHub repository

https://github.com/shobhit1kapoor/lore-app

## Architecture overview

https://github.com/shobhit1kapoor/lore-app/blob/main/docs/protegrity-architecture.md

LORE places an isolated Protegrity Privacy Gateway between transient ingress and every persistent or AI boundary. The gateway is the only service holding Developer Edition credentials. It discovers sensitive data, protects the complete canonical source, creates a pseudonymized minimum-necessary AI view, rescans its postcondition, and applies input and output Semantic Guardrails. Protected context is then used by scoped organizational-memory tools and a provider-neutral NVIDIA adapter. Exact provider payloads are destination-scanned without being logged, responses are scanned before release, and every stage produces an append-only hash-chained Protection Receipt.

The working implementation demonstrates protection across ingestion, persistent memory, retrieval and tools, inference, response generation, and evidence logging. Protegrity failures block persistence and model calls instead of falling back to unprotected processing.

## Demo video — 10 minutes 34 seconds

https://github.com/shobhit1kapoor/lore-app/releases/download/v1.0-hackathon-demo/Lore_Protegrity_Final_Demo.mp4

The walkthrough shows the live Privacy Control Center, isolated Protegrity boundary, protected input operation, real Protegrity-to-NVIDIA inference, destination scanning, complete trace receipts, Attack Lab defenses, protected organizational memory, credential isolation, and fail-closed live verification.

## Optional Developer Edition feedback

https://github.com/shobhit1kapoor/lore-app/blob/main/docs/developer-feedback.md

The project uses synthetic data only and makes no compliance, certification, or production-readiness claim.

Thank you for your consideration.

Best regards,  
Shobhit Kapoor
